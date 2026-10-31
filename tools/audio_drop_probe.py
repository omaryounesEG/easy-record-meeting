# -*- coding: utf-8 -*-
"""Reproduce the reported defect: audio dies while video keeps recording.

Plays a continuous 440 Hz tone on the default output, records video+audio for
`--seconds` seconds, samples the reported level once a second, then analyses the
audio track of the produced MP4 in 5-second windows.

Usage:
    python tools/audio_drop_probe.py --seconds 70
    python tools/audio_drop_probe.py --seconds 20 --pause 3
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import subprocess
import sys
import threading
import time
import wave

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
os.environ.setdefault("EASYRECT_KEEP_TEMP", "1")

OUT_DIR = os.path.join(HERE, "reports", "probe_media")


def make_tone(path: str, seconds: int = 30, freq: int = 440, rate: int = 48000) -> None:
    import math
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = bytearray()
        for i in range(rate * seconds):
            value = int(12000 * math.sin(2 * math.pi * freq * i / rate))
            frames += struct.pack("<hh", value, value)
        w.writeframes(bytes(frames))


def play_loop(path: str) -> None:
    import winsound
    winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)


def stop_play() -> None:
    import winsound
    winsound.PlaySound(None, winsound.SND_PURGE)


def audio_windows(ffmpeg: str, media: str, window: float = 5.0):
    """Return [(start, mean_volume_db)] for the audio track of `media`."""
    duration = None
    probe = subprocess.run([ffmpeg, "-hide_banner", "-i", media],
                           capture_output=True, text=True, errors="ignore")
    for line in probe.stderr.splitlines():
        if "Duration:" in line:
            hms = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = hms.split(":")
            duration = int(h) * 3600 + int(m) * 60 + float(s)
            break
    if not duration:
        return []
    rows = []
    start = 0.0
    while start < duration:
        out = subprocess.run(
            [ffmpeg, "-hide_banner", "-nostats", "-ss", f"{start:.2f}", "-t", f"{window:.2f}",
             "-i", media, "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True, errors="ignore")
        mean = None
        for line in out.stderr.splitlines():
            if "mean_volume:" in line:
                mean = float(line.split("mean_volume:")[1].split("dB")[0])
        rows.append((round(start, 1), mean))
        start += window
    return rows


def run_case(engine_mod, seconds: float, pause_at: float | None, pause_len: float, tag: str):
    from easyrec import engine as eng

    devices = eng.list_devices()
    if not devices:
        raise SystemExit("no loopback device found")
    device = devices[0]
    recorder = eng.Recorder()
    samples = []
    target = recorder.start(mode="video", directory=OUT_DIR, device=device,
                            name_prefix=f"drop_{tag}")
    print(f"[{tag}] target={target} device={device.name}")

    started = time.monotonic()
    paused_at = None
    resumed_at = None
    while time.monotonic() - started < seconds:
        snap = recorder.snapshot()
        samples.append((round(time.monotonic() - started, 1), round(snap.level, 1),
                        snap.status, snap.error or ""))
        if pause_at is not None and paused_at is None and time.monotonic() - started >= pause_at:
            recorder.pause()
            paused_at = time.monotonic() - started
            print(f"[{tag}] pause at {paused_at:.1f}s")
        if paused_at is not None and resumed_at is None and \
                time.monotonic() - started >= pause_at + pause_len:
            recorder.resume()
            resumed_at = time.monotonic() - started
            print(f"[{tag}] resume at {resumed_at:.1f}s")
        time.sleep(1.0)

    result = recorder.stop()
    print(f"[{tag}] status={result.status} error={result.error} duration={result.elapsed:.1f}s")
    return result, samples


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=70)
    parser.add_argument("--pause", type=float, default=None)
    parser.add_argument("--pause-len", type=float, default=3.0)
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    tone = os.path.join(OUT_DIR, "tone_loop.wav")
    if not os.path.exists(tone):
        make_tone(tone, seconds=30)

    from easyrec import engine as eng
    import easyrec.engine as engine_mod

    play_loop(tone)
    time.sleep(1.0)
    try:
        tag = "pause" if args.pause is not None else "plain"
        result, samples = run_case(engine_mod, args.seconds, args.pause,
                                   args.pause_len, tag)
    finally:
        stop_play()

    out = result.output_path or os.path.join(OUT_DIR, f"drop_{tag}.mp4")
    ffmpeg = eng.resolve_ffmpeg()
    windows = audio_windows(ffmpeg, out) if out and os.path.exists(out) else []
    print("\nlevel samples (t, level, status):")
    for row in samples:
        print("   ", row)
    print("\naudio mean volume per 5 s window:")
    for start, mean in windows:
        print(f"    {start:>5.1f}s  {mean} dB")

    quiet = [w for w in windows if w[1] is not None and w[1] <= -60]
    report = {
        "case": "pause" if args.pause is not None else "plain",
        "seconds": args.seconds,
        "status": result.status,
        "error": result.error,
        "elapsed": round(result.elapsed, 1),
        "windows": windows,
        "silent_windows": len(quiet),
        "level_series": samples,
    }
    with open(os.path.join(OUT_DIR, "drop_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print("\nsilent(< -60 dB) windows:", len(quiet))
    print("written:", os.path.join(OUT_DIR, "drop_report.json"))


if __name__ == "__main__":
    main()
