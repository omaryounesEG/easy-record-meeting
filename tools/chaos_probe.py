# -*- coding: utf-8 -*-
"""Kill the screen-capture ffmpeg mid-recording and prove nothing is lost.

    python tools/chaos_probe.py --seconds 100 --kill-at 25,60

The audio must be continuous across every kill and the final file must keep both
streams; a failed picture is allowed, a silent file is not.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
OUT = os.path.join(HERE, "reports", "probe_media")


def ffmpeg_count() -> int:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq ffmpeg.exe", "/NH"],
                         capture_output=True, text=True).stdout
    return out.lower().count("ffmpeg.exe")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=100)
    parser.add_argument("--kill-at", default="25,60")
    args = parser.parse_args()
    kills = [float(x) for x in args.kill_at.split(",") if x.strip()]

    from easyrec import engine
    import winsound

    os.makedirs(OUT, exist_ok=True)
    tone = os.path.join(OUT, "tone_loop.wav")
    winsound.PlaySound(tone, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
    time.sleep(0.8)

    device = engine.list_devices()[0]
    rec = engine.Recorder()
    out = rec.start(mode="video", directory=OUT, device=device, name_prefix="chaos")
    print("started", out, flush=True)

    started = time.monotonic()
    pending = list(kills)
    while time.monotonic() - started < args.seconds:
        elapsed = time.monotonic() - started
        if pending and elapsed >= pending[0]:
            pending.pop(0)
            count = ffmpeg_count()
            print(f"t={elapsed:.0f}s killing ffmpeg (running={count})", flush=True)
            subprocess.run(["taskkill", "/F", "/IM", "ffmpeg.exe"],
                           capture_output=True, text=True)
        snap = rec.snapshot()
        if int(elapsed) % 10 == 0:
            print(f"  t={elapsed:5.0f}s level={snap.level:5.1f} seg={snap.segments} "
                  f"notice={snap.notice!r}", flush=True)
        time.sleep(1.0)

    result = rec.stop()
    winsound.PlaySound(None, winsound.SND_PURGE)
    print(f"RESULT status={result.status} elapsed={result.elapsed:.0f}s "
          f"segments={result.segments} size={result.file_size // 1048576}MB "
          f"error={result.error}", flush=True)

    if not result.output_path or not os.path.exists(result.output_path):
        raise SystemExit("no output file")

    ffmpeg = engine.resolve_ffmpeg()
    info = subprocess.run([ffmpeg, "-hide_banner", "-i", result.output_path],
                          capture_output=True, text=True, errors="ignore").stderr
    has_audio = "Audio:" in info
    print("has audio track:", has_audio, flush=True)

    duration = 0.0
    for line in info.splitlines():
        if "Duration:" in line:
            hms = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = hms.split(":")
            duration = int(h) * 3600 + int(m) * 60 + float(s)
    print("duration:", duration, flush=True)

    silent = 0
    start = 0.0
    while start < duration:
        vol = subprocess.run(
            [ffmpeg, "-hide_banner", "-nostats", "-ss", f"{start:.1f}", "-t", "5",
             "-i", result.output_path, "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True, errors="ignore").stderr
        mean = None
        for line in vol.splitlines():
            if "mean_volume:" in line:
                mean = float(line.split("mean_volume:")[1].split("dB")[0])
        if mean is None or mean <= -60:
            silent += 1
            print(f"  SILENT window at {start:.0f}s (mean={mean})", flush=True)
        start += 5
    print("silent windows:", silent, flush=True)
    print("VERDICT:", "PASS" if has_audio and silent == 0 else "FAIL")


if __name__ == "__main__":
    main()
