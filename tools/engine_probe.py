# -*- coding: utf-8 -*-
"""End-to-end engine probe: real loopback capture (audio + video), real muxing.

Plays a tone through the speakers, records the loopback for a few seconds,
then verifies the produced files with ffmpeg (duration, streams, size).
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import winsound

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from easyrec import engine

OUT = os.path.join(HERE, "reports", "probe_media")
os.makedirs(OUT, exist_ok=True)


def tone(seconds: float, freq: int = 660) -> None:
    try:
        winsound.Beep(freq, int(seconds * 1000))
    except Exception:
        pass


def streams(path: str) -> str:
    proc = subprocess.run([engine.resolve_ffmpeg(), "-hide_banner", "-i", path],
                          stderr=subprocess.PIPE, text=True, errors="replace")
    text = proc.stderr or ""
    dur = ""
    kinds = []
    for line in text.splitlines():
        if "Duration:" in line:
            dur = line.split("Duration:")[1].split(",")[0].strip()
        if "Stream #" in line:
            kinds.append(line.split("Stream #")[1].strip()[:60])
    return f"duration={dur} streams={kinds}"


def main() -> int:
    devices = engine.list_devices()
    print(f"loopback devices: {len(devices)}")
    for dev in devices:
        print("  -", dev.name)
    if not devices:
        print("NO DEVICE -> cannot test capture")
        return 2

    device = devices[0]
    recorder = engine.Recorder()

    # ---------------------------------------------------------------- audio
    print("\n[audio] recording 3.5s ...")
    t0 = time.monotonic()
    path = recorder.start(mode="audio", directory=OUT, device=device,
                          name_prefix="probe_audio")
    threading.Thread(target=tone, args=(3.0, 720), daemon=True).start()
    peak = 0.0
    while time.monotonic() - t0 < 3.4:
        snap = recorder.snapshot()
        peak = max(peak, snap.level)
        time.sleep(0.1)
    snap = recorder.stop()
    print(f"  status={snap.status} error={snap.error} peak_level={peak:.1f}%")
    print(f"  file={snap.output_path} size={os.path.getsize(snap.output_path) if snap.output_path and os.path.exists(snap.output_path) else 0}")
    if snap.output_path and os.path.exists(snap.output_path):
        print("  ", streams(snap.output_path))

    # ---------------------------------------------------------------- video
    print("\n[video] recording 4.5s ...")
    t0 = time.monotonic()
    path = recorder.start(mode="video", directory=OUT, device=device,
                          name_prefix="probe_video")
    threading.Thread(target=tone, args=(4.0, 520), daemon=True).start()
    time.sleep(1.0)
    recorder.pause()                    # exercise segmenting
    time.sleep(1.0)
    recorder.resume()
    peak = 0.0
    while time.monotonic() - t0 < 5.0:
        snap = recorder.snapshot()
        peak = max(peak, snap.level)
        time.sleep(0.1)
    snap = recorder.stop(timeout=60)
    print(f"  status={snap.status} error={snap.error} segments={snap.segments} peak={peak:.1f}%")
    if snap.output_path and os.path.exists(snap.output_path):
        print(f"  file={snap.output_path} size={os.path.getsize(snap.output_path)/1024:.0f} KB")
        print("  ", streams(snap.output_path))
    else:
        print("  MISSING OUTPUT")
    leftovers = [f for f in os.listdir(OUT) if f.startswith(".")]
    print("  temp leftovers:", leftovers)
    return 0 if snap.status == "done" else 1


if __name__ == "__main__":
    raise SystemExit(main())
