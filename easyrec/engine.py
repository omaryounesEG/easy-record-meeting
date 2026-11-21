# -*- coding: utf-8 -*-
"""Recording engine — deliberately free of Tk so it can be unit-tested.

Design notes
------------
* One thread decodes the loopback device; the UI never touches numpy.
* The UI *polls* ``snapshot()`` every 250 ms instead of receiving callbacks from
  worker threads (Tk is not thread-safe and ``after()`` from a foreign thread is
  undefined behaviour).
* ``stop()`` joins the writer thread **before** muxing.  v1 muxed immediately
  after setting the stop event, so ffmpeg could read a WAV that was still being
  buffered by libsndfile; long recordings could lose their tail or fail to mux.
* Pause is implemented as *segments*: video and audio both stop, and a new
  segment starts on resume.  v1 kept recording the screen while discarding the
  audio, so every pause permanently desynced picture from sound.
* Failures are never swallowed: every error surfaces through ``state.error``.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

SAMPLE_RATE = 44100
CHANNELS = 2
CHUNK_FRAMES = SAMPLE_RATE // 4          # 0.25 s of audio per read
WARN_AFTER = 10.0                        # seconds of silence -> warning
CRITICAL_AFTER = 30.0                    # seconds of silence -> alarm
MP3_BITRATE = 128
AUDIO_STALL_SECONDS = 12.0                # device silence (after real sound) -> restart stream
AUDIO_RECOVERIES = 3                      # stream restarts allowed per segment
AUDIO_HARD_STALL = 20.0                   # no audio chunks at all -> roll a new segment
VIDEO_HARD_STALL = 12.0                   # ffmpeg silent -> roll a new segment
VIDEO_RETRY_SECONDS = 10.0                # wait before retrying a failed capture
AUDIO_ROLL_BYTES = int(3.5 * 1024 ** 3)   # a WAV must stay well under 4 GB
AUDIO_PROBE_SECONDS = 0.4                 # quick level probe when picking a fallback
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class AudioStalled(RuntimeError):
    """The loopback device delivered pure silence: the endpoint most likely slept."""


class RecorderError(RuntimeError):
    pass


# --------------------------------------------------------------------- helpers
def resolve_ffmpeg() -> str:
    """Locate ffmpeg: next to the exe/script first, then bundled, then PATH."""
    candidates: List[str] = []
    here = os.path.dirname(os.path.abspath(__file__))
    bases = [os.path.dirname(here)]
    if getattr(sys, "frozen", False):
        bases.append(os.path.dirname(os.path.abspath(sys.executable)))
    for base in bases:
        candidates.append(os.path.join(base, "ffmpeg.exe"))
    candidates.append(os.path.join(os.path.expanduser("~"), "bin", "ffmpeg.exe"))
    for path in candidates:
        if path and os.path.exists(path):
            return path
    try:                                    # optional dependency
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    return shutil.which("ffmpeg") or "ffmpeg"


def format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    mins, secs = divmod(seconds, 60)
    hrs, mins = divmod(mins, 60)
    return f"{hrs:02d}:{mins:02d}:{secs:02d}"


def parse_timestamp(text: str) -> float:
    """``HH:MM:SS`` / ``MM:SS`` / ``SS`` -> seconds. Raises ValueError."""
    raw = (text or "").strip().replace(",", ".").replace("٫", ".")
    if not raw:
        raise ValueError("empty timestamp")
    if raw.startswith("-"):
        raise ValueError("negative")
    parts = raw.split(":")
    if len(parts) > 3:
        raise ValueError("too many parts")
    try:
        values = [float(p) for p in parts]
    except ValueError:
        raise ValueError("not a number")
    if any(v < 0 for v in values):
        raise ValueError("negative")
    if len(values) == 3:
        return values[0] * 3600 + values[1] * 60 + values[2]
    if len(values) == 2:
        return values[0] * 60 + values[1]
    return values[0]


def safe_name(prefix: str, when: Optional[datetime] = None) -> str:
    """Create a file name that is valid on Windows for Arabic and English."""
    when = when or datetime.now()
    cleaned = "".join(ch for ch in (prefix or "Recording") if ch.isalnum() or ch in " -_")
    cleaned = "_".join(cleaned.split()) or "Recording"
    return f"{cleaned}_{when.strftime('%Y-%m-%d_%H-%M-%S')}"


# ----------------------------------------------------------------------- state
@dataclass(frozen=True)
class Snapshot:
    status: str = "idle"          # idle|recording|paused|finishing|done|error
    mode: str = "video"
    elapsed: float = 0.0
    level: float = 0.0
    silence: float = 0.0
    alert: str = "none"           # none|warn|critical
    alarm_muted: bool = False
    file_size: int = 0
    output_path: Optional[str] = None
    error: Optional[str] = None
    segments: int = 0
    notice: str = ""              # transient message ("audio stream restarted")
    notice_key: str = ""          # i18n key for that message

    @property
    def is_active(self) -> bool:
        return self.status in ("recording", "paused", "finishing")


# --------------------------------------------------------------------- devices
_INDEX_PREFIX = re.compile(r"\(\s*\d+\s*-\s*")


def device_key(name: str) -> str:
    """Comparison key for an endpoint name.

    Windows appends a changing instance index ("Speakers (2- Logi USB Headset)")
    and soundcard repeats it, so two enumerations of the same speaker can differ
    by a single digit.  Stripping the index makes the comparison stable.
    """
    return _INDEX_PREFIX.sub("(", (name or "").strip().lower())


def init_com() -> None:
    """soundcard talks to Media Foundation: every thread needs COM initialised."""
    try:
        import ctypes
        ctypes.windll.ole32.CoInitializeEx(None, 0x2)      # COINIT_MULTITHREADED
    except Exception:
        pass


def list_devices():
    """Loopback (playback) devices, default speaker first."""
    init_com()
    import soundcard as sc
    mics = sc.all_microphones(include_loopback=True)
    loopbacks = [m for m in mics if getattr(m, "isloopback", False)]
    default_name = getattr(sc.default_speaker(), "name", "")

    def score(dev):
        return 0 if default_name and default_name in dev.name else 1

    return sorted(loopbacks, key=score)


# -------------------------------------------------------------------- recorder
class Recorder:
    """Audio (+ optional screen) recorder with pause, silence alarm and muxing."""

    def __init__(self, ffmpeg: Optional[str] = None, device_factory=None,
                 warn_after: float = WARN_AFTER, critical_after: float = CRITICAL_AFTER):
        self.ffmpeg = ffmpeg or resolve_ffmpeg()
        self._device_factory = device_factory   # test seam
        self.warn_after = warn_after
        self.critical_after = critical_after
        self._lock = threading.RLock()
        self._status = "idle"
        self._mode = "video"
        self._level = 0.0
        self._alarm_muted = False
        self._error: Optional[str] = None
        self._output: Optional[str] = None
        self._base: Optional[str] = None
        self._accumulated = 0.0
        self._period_start = 0.0
        self._last_sound = 0.0
        self._silence = 0.0
        self._thread: Optional[threading.Thread] = None
        self._seg_stop: Optional[threading.Event] = None
        self._had_sound = False
        self._notice = ""
        self._notice_key = "notice.audio_reconnect"
        self._notice_at = 0.0
        self._device_name = ""
        self._audio_beat = 0.0            # last moment a chunk arrived
        self._chunks = 0                  # audio chunks written this segment
        self._segment_started = 0.0
        self._log_path: Optional[str] = None
        self._lost_rolls = 0              # consecutive segments rolled without audio
        self._audio_token = None          # only the owner writes to the segment
        self._video_progress = None
        self._video_size = (1920, 1080)
        self._video_down_until = 0.0
        self._wd_stop = threading.Event()
        self._wd_thread: Optional[threading.Thread] = None
        self._video: Optional[subprocess.Popen] = None
        self._segments: List[Dict[str, Any]] = []
        self._video_log: Optional[str] = None
        self._last_device = None
        self._segment_count = 0
        self.beeps = 0

    # ------------------------------------------------------------------ query
    def snapshot(self) -> Snapshot:
        with self._lock:
            elapsed = self._accumulated
            if self._status == "recording":
                elapsed += time.monotonic() - self._period_start
            size = 0
            if self._mode == "audio":
                check = self._output
            else:
                segs = [s for s in self._segments if os.path.exists(s["video"])]
                check = segs[-1]["video"] if segs else None
                size = sum(os.path.getsize(s["video"]) for s in segs)
                if segs:                       # buffered writer: ask ffmpeg itself
                    reported = self._progress_size(segs[-1].get("progress"))
                    if reported:
                        size = sum(os.path.getsize(x["video"]) for x in segs[:-1]) + reported
            if check and self._mode == "audio" and os.path.exists(check):
                try:
                    size = os.path.getsize(check)
                except OSError:
                    size = 0
            silence = self._silence
            if self._status == "recording":
                silence = 0.0 if self._level >= 1.0 else max(0.0, time.monotonic() - self._last_sound)
            alert = "none"
            if self._status == "recording":
                if silence >= self.critical_after:
                    alert = "critical"
                elif silence >= self.warn_after:
                    alert = "warn"
            return Snapshot(
                status=self._status,
                mode=self._mode,
                elapsed=elapsed,
                level=(self._level
                       if self._status == "recording"
                       and time.monotonic() - self._audio_beat < 1.5 else 0.0),
                silence=silence,
                alert=alert,
                alarm_muted=self._alarm_muted,
                file_size=size,
                output_path=self._output,
                error=self._error,
                segments=max(self._segment_count, len(self._segments)),
                notice=(self._notice
                        if self._notice and time.monotonic() - self._notice_at < 20 else ""),
                notice_key=(self._notice_key
                            if self._notice and time.monotonic() - self._notice_at < 20
                            else ""),
            )

    def _progress_size(self, path: Optional[str]) -> int:
        if not path or not os.path.exists(path):
            return 0
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                lines = fh.read().splitlines()[-40:]
            for line in reversed(lines):
                if line.startswith("total_size="):
                    return int(line.split("=", 1)[1].strip() or 0)
        except Exception:
            return 0
        return 0

    @property
    def status(self) -> str:
        with self._lock:
            return self._status

    def mute_alarm(self) -> None:
        with self._lock:
            self._alarm_muted = True

    # ------------------------------------------------------------------ start
    def start(self, *, mode: str, directory: str, device, name_prefix: str = "Recording") -> str:
        with self._lock:
            if self._status in ("recording", "paused", "finishing"):
                raise RecorderError("a recording is already running")
            if device is None:
                raise RecorderError("no audio device")
            mode = "audio" if mode == "audio" else "video"
            os.makedirs(directory, exist_ok=True)
            self._last_device = device
            self._device_name = getattr(device, "name", "") or ""

            base = safe_name(name_prefix)
            ext = ".mp4" if mode == "video" else ".mp3"
            self._mode = mode
            self._base = base
            self._output = os.path.join(directory, base + ext)
            self._error = None
            self._level = 0.0
            self._alarm_muted = False
            self._accumulated = 0.0
            self._period_start = time.monotonic()
            self._last_sound = time.monotonic()
            self._silence = 0.0
            self._audio_beat = time.monotonic()
            self._segments = []
            self._segment_count = 0
            self._had_sound = False
            self._notice = ""
            self._notice_key = "notice.audio_reconnect"
            self._notice_at = 0.0
            self.beeps = 0
            self._status = "recording"

        try:
            self._begin_segment(device)
        except Exception as exc:
            # the user asked for video, but losing the meeting would be worse:
            # start the sound and keep retrying the picture
            if self._mode == "video":
                self._log(f"initial screen capture failed: {exc}")
                try:
                    self._begin_segment(device, with_video=False)
                    self._video_down_until = time.monotonic() + VIDEO_RETRY_SECONDS
                    self._note("screen capture is unavailable — audio keeps recording",
                               "notice.video_lost")
                except Exception as exc2:
                    with self._lock:
                        self._status = "error"
                        self._error = str(exc2)
                    self._cleanup_segments()
                    raise RecorderError(str(exc2)) from exc2
            else:
                with self._lock:
                    self._status = "error"
                    self._error = str(exc)
                self._cleanup_segments()
                raise RecorderError(str(exc)) from exc
        self._start_watchdog()
        self._log(f"start mode={self._mode} device={self._device_name!r} out={self._output}")
        return self._output

    # ------------------------------------------------------------------ logging
    def _log(self, message: str) -> None:
        """Append one line to %APPDATA%/EasyRecord/recorder.log (best effort)."""
        try:
            if not self._log_path:
                import tempfile
                from .config import config_path
                base = os.path.dirname(config_path())
                os.makedirs(base, exist_ok=True)
                self._log_path = os.path.join(base, "recorder.log")
            stamp = time.strftime("%Y-%m-%d %H:%M:%S")
            line = f"{stamp} {message}\n"
            if os.path.exists(self._log_path) and os.path.getsize(self._log_path) > 2_000_000:
                os.replace(self._log_path, self._log_path + ".1")
            with open(self._log_path, "a", encoding="utf-8") as fh:
                fh.write(line)
        except Exception:
            pass

    # ---------------------------------------------------------------- watchdog
    def _start_watchdog(self) -> None:
        self._wd_stop = threading.Event()
        self._wd_thread = threading.Thread(target=self._watchdog,
                                           args=(self._wd_stop,), name="easyrec-watchdog",
                                           daemon=True)
        self._wd_thread.start()

    def _stop_watchdog(self) -> None:
        self._wd_stop.set()
        thread, self._wd_thread = self._wd_thread, None
        if thread is not None:
            thread.join(3.0)

    def _video_alive(self) -> bool:
        """True while ffmpeg is running and still writing progress."""
        proc = self._video
        if proc is None:
            return False
        try:
            if proc.poll() is not None:
                return False
        except Exception:
            return False
        stamps = []
        for path in (self._video_progress, getattr(self, "_video_target", None)):
            if path:
                try:
                    stamps.append(os.path.getmtime(path))
                except OSError:
                    pass
        if stamps and time.time() - max(stamps) > VIDEO_HARD_STALL:
            return False          # alive but silent: it stopped writing
        return True

    def _watchdog(self, stop: threading.Event) -> None:
        """Roll a fresh segment when the audio or the screen capture goes quiet.

        A wedged WASAPI read never returns, so the writer thread cannot recover
        by itself: the only safe move is to start a new segment and let the mux
        step join the parts.  The same applies to a dead ffmpeg process.
        """
        last_log = time.monotonic()
        while not stop.wait(1.0):
            try:
                if self._status != "recording":
                    continue
                now = time.monotonic()
                if now - last_log >= 30.0:          # one line every 30 s
                    last_log = now
                    self._log(f"alive level={self._level:.0f} chunks={self._chunks} "
                              f"segment={len(self._segments)} audio_age={now - self._audio_beat:.1f}s "
                              f"video_ok={self._video_alive() if self._mode == 'video' else 'n/a'}")
                age = now - max(self._audio_beat, self._segment_started)
                if age > AUDIO_HARD_STALL:
                    self._roll_segment(f"audio stream stalled for {age:.0f}s — continuing")
                    continue
                if self._segments:
                    current = self._segments[-1]["audio"]
                    try:
                        if os.path.getsize(current) > AUDIO_ROLL_BYTES:
                            self._roll_segment("audio file reached 3.5 GB")
                            continue
                    except OSError:
                        pass
                if self._mode == "video":
                    if self._video is None:
                        if now >= self._video_down_until:
                            self._roll_segment("resuming the screen capture")
                        continue
                    if not self._video_alive():
                        self._roll_segment("screen capture stopped — continuing")
            except Exception:
                continue

    def _roll_segment(self, reason: str) -> None:
        """Start a new audio+video segment without touching the elapsed clock."""
        with self._lock:
            if self._status != "recording":
                return
            if self._chunks == 0:
                self._lost_rolls += 1
            else:
                self._lost_rolls = 0
            if "screen" in reason:
                key = "notice.video_reconnect"
            elif self._lost_rolls >= 2:
                key = "notice.audio_lost"
            else:
                key = "notice.audio_reconnect"
            self._log(f"roll segment ({key}): {reason}")
            self._note(reason, key)
        self._end_segment(soft=True)
        device = self._fresh_device() or self._last_device
        try:
            self._begin_segment(device)
            return
        except Exception as exc:                       # screen capture failed
            self._log(f"video restart failed: {exc}")
        try:                                          # keep the sound at least
            self._begin_segment(device, with_video=False)
            self._video_down_until = time.monotonic() + VIDEO_RETRY_SECONDS
            self._note("screen capture is unavailable — audio keeps recording",
                       "notice.video_lost")
            return
        except Exception as exc:
            with self._lock:
                self._status = "error"
                self._error = f"could not restart the recording stream: {exc}"

    # --------------------------------------------------------------- segments
    def _begin_segment(self, device, with_video: bool = True) -> None:
        index = len(self._segments)
        directory = os.path.dirname(self._output)
        segment = {
            "video": os.path.join(directory, f".{self._base}.{index}.video.mkv"),
            "audio": os.path.join(directory, f".{self._base}.{index}.audio.wav"),
            "progress": os.path.join(directory, f".{self._base}.{index}.progress"),
        }
        if self._mode == "video" and with_video:
            self._spawn_video(segment["video"], segment["progress"])
        self._video_progress = segment["progress"]
        self._video_target = segment["video"]
        self._segments.append(segment)
        self._seg_stop = threading.Event()
        self._audio_token = object()
        self._segment_started = time.monotonic()
        self._chunks = 0
        self._thread = threading.Thread(
            target=self._write_loop,
            args=(device, self._mode, segment, self._seg_stop, self._audio_token),
            name=f"easyrec-writer-{index}", daemon=True)
        self._thread.start()

    def _end_segment(self, soft: bool = False) -> None:
        # revoke ownership first: a zombie reader must never touch this segment again
        self._audio_token = None
        event = self._seg_stop
        if event is not None:
            event.set()
        thread = self._thread
        if thread is not None:
            thread.join(2.0 if soft else 8.0)
            if thread.is_alive() and not soft:
                with self._lock:
                    self._error = self._error or "the audio writer did not stop in time"
        self._thread = None
        self._seg_stop = None
        self._kill_video()

    def _spawn_video(self, target: str, progress: Optional[str] = None) -> None:
        import ctypes
        try:
            ctypes.windll.user32.SetProcessDPIAware()
            width = ctypes.windll.user32.GetSystemMetrics(0)
            height = ctypes.windll.user32.GetSystemMetrics(1)
        except Exception:
            width, height = 1920, 1080
        if width <= 0 or height <= 0:
            width, height = 1920, 1080
        self._video_size = (width, height)

        init_com()
        log_path = target + ".log"
        self._video_log = log_path
        cmd = [
            self.ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "gdigrab", "-framerate", "15",
            "-video_size", f"{width}x{height}", "-draw_mouse", "1",
            "-i", "desktop",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
            "-pix_fmt", "yuv420p", "-g", "30", "-flush_packets", "1",
        ]
        if progress:
            cmd += ["-progress", progress, "-stats_period", "1"]
        cmd += [target]
        with open(log_path, "ab", buffering=0) as log:
            self._video = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                stderr=log, creationflags=CREATE_NO_WINDOW)

        # ffmpeg buffers the matroska header, so an empty file proves nothing:
        # health is "the process is still alive after a moment".
        deadline = time.monotonic() + 1.5
        while time.monotonic() < deadline:
            if self._video.poll() is not None:
                raise RecorderError(self._ffmpeg_error() or "screen capture could not start")
            time.sleep(0.1)
        if self._video.poll() is not None:
            raise RecorderError(self._ffmpeg_error() or "screen capture could not start")

    def _mux_audio_only(self, audio: str, part: str) -> bool:
        """Screen capture failed: keep the sound on a black picture.

        A silent-video part is still a valid MP4 with the same stream layout as
        the others, so the concat step keeps one continuous file.
        """
        width, height = self._video_size
        cmd = [self.ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
               "-f", "lavfi", "-i", f"color=c=black:s={width}x{height}:r=15",
               "-i", audio, "-map", "0:v:0", "-map", "1:a:0", "-shortest",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "30",
               "-pix_fmt", "yuv420p", "-g", "30", "-c:a", "aac", "-b:a", "160k",
               part]
        try:
            done = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                  creationflags=CREATE_NO_WINDOW, timeout=3600)
        except Exception as exc:
            self._log(f"audio-only mux failed: {exc}")
            return False
        if done.returncode != 0 or not os.path.exists(part) or os.path.getsize(part) < 1024:
            self._log(f"audio-only mux exited {done.returncode}: "
                      f"{(done.stderr or b'')[-300:].decode('utf-8', 'replace')}")
            return False
        self._log("segment had no picture: the audio was kept on a black frame")
        with self._lock:
            self._notice = "the screen could not be captured — the audio was kept"
            self._notice_key = "notice.audio_kept"
            self._notice_at = time.monotonic()
        return True

    def _ffmpeg_error(self) -> str:
        try:
            if self._video_log and os.path.exists(self._video_log):
                with open(self._video_log, "rb") as fh:
                    return fh.read()[-600:].decode("utf-8", "replace").strip()
        except Exception:
            pass
        return ""

    # ------------------------------------------------------------- writer loop
    def _write_loop(self, device, mode: str, segment: Dict[str, str],
                    stop: threading.Event, token=None) -> None:
        init_com()
        try:
            if mode == "audio":
                self._encode_mp3(device, stop, token)
            else:
                self._write_wav(device, segment["audio"], stop, token)
        except Exception as exc:
            with self._lock:
                if self._status in ("recording", "paused"):
                    if self._status == "recording":
                        self._accumulated += time.monotonic() - self._period_start
                    self._error = f"audio device error: {exc}"
                    self._status = "error"
            # never keep capturing a silent picture: the user asked for sound
            self._kill_video()
            stop.set()

    def _recover_device(self):
        """Pick a loopback endpoint that can actually deliver sound.

        Order: the same endpoint (index-insensitive name) -> the system default
        speaker's loopback (the common case when a USB headset disconnects) ->
        the first endpoint that returns a real signal.
        """
        name = self._device_name or ""
        try:
            import soundcard as sc

            mics = [m for m in sc.all_microphones(include_loopback=True)
                    if getattr(m, "isloopback", False)]
        except Exception as exc:
            self._log(f"recover: enumeration failed: {exc}")
            return None, "enumeration failed"
        if not mics:
            self._log("recover: no loopback endpoints")
            return None, "no loopback endpoints"

        key = device_key(name)
        for mic in mics:
            if device_key(getattr(mic, "name", "")) == key:
                return mic, "same endpoint"
        for mic in mics:
            mic_key = device_key(getattr(mic, "name", ""))
            if key and (key in mic_key or mic_key in key):
                return mic, "name contains"
        try:
            speaker = sc.default_speaker()
            speaker_key = device_key(getattr(speaker, "name", ""))
            for mic in mics:
                if device_key(getattr(mic, "name", "")) == speaker_key:
                    return mic, "system default speaker"
        except Exception:
            pass
        for mic in mics[:4]:
            try:
                if self.probe_level(mic, AUDIO_PROBE_SECONDS) >= 1.0:
                    return mic, "probe: it has sound"
            except Exception:
                continue
        return mics[0], "first available"

    def _reconnect_device(self):
        """Backwards-compatible wrapper returning just the device."""
        return self._recover_device()[0]

    def _pump_audio(self, device, on_chunk, stop: threading.Event, token=None) -> None:
        """Read the loopback stream, restarting it when the endpoint goes dead.

        A USB or Bluetooth endpoint that sleeps keeps the WASAPI stream open but
        delivers pure silence, so the video keeps growing with no sound.  Once
        real audio has been captured, a long run of zeros is treated as a dead
        endpoint and the stream is reopened; every restart is surfaced through
        ``snapshot().notice`` so the window can tell the user.
        """
        import numpy as np

        chunk_seconds = CHUNK_FRAMES / float(SAMPLE_RATE)
        attempts = 0
        while not stop.is_set():
            if attempts:                       # a stale endpoint is replaced by name
                device = self._resolve_known_device() or device
            try:
                with device.recorder(samplerate=SAMPLE_RATE, channels=CHANNELS) as rec:
                    zero_run = 0.0
                    stall_windows = 0
                    while not stop.is_set():
                        data = rec.record(numframes=CHUNK_FRAMES)
                        if data is None or len(data) == 0:
                            continue
                        if token is not None and self._audio_token is not token:
                            return              # segment was closed under us
                        self._audio_beat = time.monotonic()
                        self._chunks += 1
                        on_chunk(data)
                        level = self._track_level(data, np)
                        if level >= 1.0:
                            zero_run = 0.0
                            stall_windows = 0
                            self._had_sound = True
                        else:
                            zero_run += chunk_seconds
                            if self._had_sound and zero_run >= AUDIO_STALL_SECONDS:
                                # keep reading through one more window before blaming the
                                # device: a quiet meeting must not cost a restart
                                zero_run = 0.0
                                stall_windows += 1
                                if stall_windows >= 2:
                                    raise AudioStalled(
                                        f"{AUDIO_STALL_SECONDS * 2:.0f}s of digital silence "
                                        "from the device")
                    return
            except Exception as exc:
                attempts += 1
                if attempts > AUDIO_RECOVERIES:
                    raise RecorderError(
                        f"the audio device stopped responding ({exc})") from exc
                self._note(f"reconnecting the audio stream ({attempts}/{AUDIO_RECOVERIES})")
                replacement, why = self._recover_device()
                self._log(f"reconnect attempt {attempts}: {type(exc).__name__}: {exc} "
                          f"-> {why} ({getattr(replacement, 'name', 'none')})")
                if replacement is not None:
                    device = replacement
                stop.wait(0.6)

    def _note(self, text: str, key: str = "notice.audio_reconnect") -> None:
        with self._lock:
            self._notice = text
            self._notice_key = key
            self._notice_at = time.monotonic()

    def _encode_mp3(self, device, stop: threading.Event, token=None) -> None:
        import lameenc
        import numpy as np

        encoder = lameenc.Encoder()
        encoder.set_bit_rate(MP3_BITRATE)
        encoder.set_in_sample_rate(SAMPLE_RATE)
        encoder.set_channels(CHANNELS)
        encoder.set_quality(2)

        tmp = self._output + ".part"

        def on_chunk(data) -> None:
            int16 = (data * 32767).clip(-32768, 32767).astype(np.int16)
            mp3.write(encoder.encode(int16.tobytes()))

        with open(tmp, "wb") as mp3:
            self._pump_audio(device, on_chunk, stop, token)
            tail = encoder.flush()
            if tail:
                mp3.write(tail)
        os.replace(tmp, self._output)

    def _write_wav(self, device, path: str, stop: threading.Event, token=None) -> None:
        import soundfile as sf

        with sf.SoundFile(path, mode="w", samplerate=SAMPLE_RATE,
                          channels=CHANNELS, format="WAV", subtype="PCM_16") as wav:
            self._pump_audio(device, wav.write, stop, token)   # close() flushes -> join before mux

    def _track_level(self, data, np) -> float:
        rms = float(np.sqrt(np.mean(np.square(data))))
        level = min(100.0, rms * 400.0)
        with self._lock:
            self._level = level
            if level >= 1.0:
                self._last_sound = time.monotonic()
                self._silence = 0.0
            else:
                self._silence = max(0.0, time.monotonic() - self._last_sound)
        return level

    # ------------------------------------------------------------------- pause
    def pause(self) -> None:
        with self._lock:
            if self._status != "recording":
                return
            self._accumulated += time.monotonic() - self._period_start
            self._status = "paused"
            self._level = 0.0
        self._end_segment()

    def _resolve_known_device(self):
        """Return the same endpoint re-enumerated, or None when it is not listed."""
        name = self._device_name
        if not name:
            return None
        try:
            for candidate in list_devices():
                if getattr(candidate, "name", "") == name:
                    return candidate
        except Exception:
            return None
        return None

    def _fresh_device(self):
        """Re-resolve the endpoint by name, falling back to the current default."""
        name = self._device_name
        try:
            devices = list_devices()
        except Exception:
            return self._last_device
        if name:
            key = device_key(name)
            for candidate in devices:
                if device_key(getattr(candidate, "name", "")) == key:
                    return candidate
        # the endpoint disappeared (headset slept/unplugged): use the default output
        if devices:
            self._note("the audio device changed — following the system default")
            return devices[0]
        return self._last_device

    def resume(self) -> None:
        device = self._fresh_device()
        with self._lock:
            if self._status != "paused" or device is None:
                return
            self._status = "recording"
            self._period_start = time.monotonic()
            self._last_sound = time.monotonic()
            self._alarm_muted = False
        try:
            self._begin_segment(device)
        except Exception as exc:
            with self._lock:
                self._status = "error"
                self._error = str(exc)

    # -------------------------------------------------------------------- stop
    def stop(self, timeout: float = 20.0) -> Snapshot:
        with self._lock:
            if self._status not in ("recording", "paused", "error"):
                return self.snapshot()
            failed = self._status == "error"
            if self._status == "recording":
                self._accumulated += time.monotonic() - self._period_start
            self._status = "finishing"
            self._level = 0.0
        self._stop_watchdog()
        self._end_segment()          # joins the writer and kills ffmpeg, even after an error

        if self._mode == "video":
            self._finalize_video()
        else:
            self._finalize_audio()

        with self._lock:
            if not failed and self._status != "error":
                self._status = "done"
            elif failed and os.path.exists(self._output or ""):
                self._error = (self._error or "recording failed") + " — the captured part was kept"
            snap = self.snapshot()
        self._log(f"stop status={snap.status} elapsed={snap.elapsed:.0f}s "
                  f"segments={snap.segments} size={snap.file_size} "
                  f"notice={snap.notice!r} error={snap.error!r}")
        return snap

    def _finalize_audio(self) -> None:
        path = self._output
        if not path or not os.path.exists(path) or os.path.getsize(path) == 0:
            with self._lock:
                self._error = self._error or "the audio file is empty"
                self._status = "error"

    def _finalize_video(self) -> None:
        parts: List[str] = []
        for index, segment in enumerate(self._segments):
            part = os.path.join(os.path.dirname(self._output), f".{self._base}.{index}.mp4")
            if self._mux_segment(segment, part):
                parts.append(part)
            elif index == 0:
                with self._lock:
                    self._error = self._error or (self._ffmpeg_error() or "no video was captured")
                    self._status = "error"
                self._cleanup_segments()
                self._cleanup_paths(parts)
                return

        if not parts:
            with self._lock:
                self._error = self._error or "no segments were captured"
                self._status = "error"
            self._cleanup_segments()
            return

        if len(parts) == 1:
            os.replace(parts[0], self._output)
        else:
            listing = os.path.join(os.path.dirname(self._output), f".{self._base}.concat.txt")
            with open(listing, "w", encoding="utf-8") as fh:
                for part in parts:
                    escaped = part.replace("'", "'\\''")
                    fh.write(f"file '{escaped}'\n")
            cmd = [self.ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                   "-f", "concat", "-safe", "0", "-i", listing,
                   "-c", "copy", "-movflags", "+faststart", self._output]
            done = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                  creationflags=CREATE_NO_WINDOW, timeout=1800)
            if done.returncode != 0 or not os.path.exists(self._output):
                detail = (done.stderr or b"")[-400:].decode("utf-8", "replace").strip()
                with self._lock:
                    self._error = f"concat failed: {detail or 'ffmpeg error'}"
                    self._status = "error"
                self._cleanup_paths(parts + [listing])
                self._cleanup_segments()
                return
            self._cleanup_paths([listing])
            self._cleanup_paths(parts)

        self._cleanup_segments()

    def _mux_segment(self, segment: Dict[str, str], part: str) -> bool:
        video, audio = segment["video"], segment["audio"]
        video_ok = os.path.exists(video) and os.path.getsize(video) > 1024
        audio_ok = os.path.exists(audio) and os.path.getsize(audio) > 1024
        if not video_ok:
            if audio_ok:                       # never throw the sound away
                return self._mux_audio_only(audio, part)
            with self._lock:
                self._error = (f"video segment missing ({os.path.basename(video)}, "
                               f"{os.path.getsize(video) if os.path.exists(video) else 'absent'} bytes)")
            return False
        cmd = [self.ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", video]
        if audio_ok:
            cmd += ["-i", audio, "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k"]
        else:
            cmd += ["-an", "-c:v", "copy"]
            with self._lock:
                self._notice = "a segment was saved without sound"
                self._notice_key = "notice.no_audio"
                self._notice_at = time.monotonic()
        cmd += [part]
        try:
            done = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                  creationflags=CREATE_NO_WINDOW, timeout=1800)
        except Exception as exc:
            with self._lock:
                self._error = f"mux failed: {exc}"
            return False
        if done.returncode != 0:
            detail = (done.stderr or b"")[-500:].decode("utf-8", "replace").strip()
            with self._lock:
                self._error = f"mux failed: {detail or 'ffmpeg error'}"
            return False
        return os.path.exists(part) and os.path.getsize(part) > 0

    def _kill_video(self) -> None:
        proc, self._video = self._video, None
        if not proc:
            return
        try:                       # 'q' on stdin = graceful quit, flushes the file
            if proc.stdin:
                proc.stdin.write(b"q")
                proc.stdin.flush()
                proc.stdin.close()
        except Exception:
            pass
        try:
            proc.wait(timeout=10)
            return
        except Exception:
            pass
        try:
            proc.terminate()
            proc.wait(timeout=8)
        except Exception:
            try:
                proc.kill()
                proc.wait(timeout=5)
            except Exception:
                pass

    def _cleanup_paths(self, paths) -> None:
        for path in paths:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

    def _cleanup_segments(self) -> None:
        self._segment_count = max(self._segment_count, len(self._segments))
        if os.environ.get("EASYRECT_KEEP_TEMP"):
            self._segments = []
            return
        leftovers: List[str] = []
        for segment in self._segments:
            leftovers += [segment["video"], segment["audio"], segment["video"] + ".log",
                          segment.get("progress", "")]
        self._cleanup_paths(leftovers)
        self._segments = []

    # ------------------------------------------------------------------- misc
    def cancel(self) -> None:
        """Abort without muxing (app closing mid-recording)."""
        with self._lock:
            self._status = "idle"
        self._stop_watchdog()
        self._end_segment()
        self._cleanup_segments()

    def probe_level(self, device, seconds: float = 1.0) -> float:
        """Measure the device level for ``seconds`` (signal test)."""
        import numpy as np
        init_com()
        frames = int(SAMPLE_RATE * max(0.2, min(seconds, 3.0)))
        with device.recorder(samplerate=SAMPLE_RATE, channels=CHANNELS) as rec:
            data = rec.record(numframes=frames)
        if data is None or len(data) == 0:
            return 0.0
        return min(100.0, float(np.sqrt(np.mean(np.square(data)))) * 400.0)


def cut_segment(ffmpeg: str, source: str, start: float, end: float,
                destination: str) -> subprocess.CompletedProcess:
    """Stream-copy ``start..end`` into ``destination`` (no re-encode)."""
    if not (end > start):
        raise ValueError("end must be greater than start")
    duration = max(0.05, end - start)
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
           "-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", source,
           "-map", "0", "-c", "copy", "-avoid_negative_ts", "make_zero",
           destination]
    return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                          creationflags=CREATE_NO_WINDOW, timeout=900)


def media_duration(ffmpeg: str, path: str) -> float:
    try:
        proc = subprocess.run([ffmpeg, "-hide_banner", "-i", path],
                              stderr=subprocess.PIPE, stdout=subprocess.DEVNULL,
                              creationflags=CREATE_NO_WINDOW, timeout=60,
                              text=True, errors="replace")
    except Exception:
        return 0.0
    for line in (proc.stderr or "").splitlines():
        if "Duration:" in line:
            part = line.split("Duration:")[1].split(",")[0].strip()
            try:
                return parse_timestamp(part)
            except ValueError:
                return 0.0
    return 0.0
