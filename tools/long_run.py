# -*- coding: utf-8 -*-
"""Long-run soak test: record video+audio for many minutes and log health every 10 s.

    python tools/long_run.py --minutes 25

Writes reports/long_run.log and leaves the media in reports/probe_media.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
os.environ.setdefault("EASYRECT_KEEP_TEMP", "0")

OUT = os.path.join(HERE, "reports", "probe_media")
LOG = os.path.join(HERE, "reports", "long_run.log")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=float, default=25)
    parser.add_argument("--mode", default="video")
    args = parser.parse_args()

    from easyrec import engine

    devices = engine.list_devices()
    if not devices:
        raise SystemExit("no loopback device")
    device = devices[0]

    # keep sound flowing: loop a tone so silence is never the cause
    import struct
    import wave

    tone = os.path.join(OUT, "tone_loop.wav")
    os.makedirs(OUT, exist_ok=True)
    if not os.path.exists(tone):
        with wave.open(tone, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(48000)
            frames = bytearray()
            for i in range(48000 * 30):
                v = int(9000 * __import__("math").sin(2 * 3.141592653589793 * 440 * i / 48000))
                frames += struct.pack("<hh", v, v)
            w.writeframes(bytes(frames))
    import winsound
    winsound.PlaySound(tone, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
    time.sleep(1.0)

    rec = engine.Recorder()
    out = rec.start(mode=args.mode, directory=OUT, device=device,
                    name_prefix="soak")
    started = time.monotonic()
    print(f"soak start {out} device={device.name}", flush=True)

    last_alerts = 0
    with open(LOG, "w", encoding="utf-8") as fh:
        fh.write(f"# soak {args.mode} {args.minutes} min device={device.name}\n")
        for tick in range(int(args.minutes * 60)):
            time.sleep(1.0)
            snap = rec.snapshot()
            if tick % 10 == 0 or snap.alert != "none" or snap.notice:
                line = (f"{snap.elapsed:7.1f}s level={snap.level:5.1f} status={snap.status} "
                        f"seg={snap.segments} size={snap.file_size // 1048576}MB "
                        f"alert={snap.alert} notice={snap.notice!r}")
                fh.write(line + "\n")
                fh.flush()
                print(line, flush=True)
                if snap.alert != "none":
                    last_alerts += 1
            if snap.status not in ("recording", "paused"):
                fh.write(f"stopped early: {snap.status} {snap.error}\n")
                break

    result = rec.stop()
    winsound.PlaySound(None, winsound.SND_PURGE)
    summary = (f"RESULT status={result.status} elapsed={result.elapsed:.0f}s "
               f"segments={result.segments} size={result.file_size // 1048576}MB "
               f"alerts={last_alerts} error={result.error}")
    print(summary, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(summary + "\n")
    print("file:", result.output_path)


if __name__ == "__main__":
    main()
