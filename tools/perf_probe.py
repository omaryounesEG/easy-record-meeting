# -*- coding: utf-8 -*-
"""Performance probe: measures the numbers quoted in reports/PERFORMANCE_TEST.md.

Writes reports/perf.json so the report is generated from real measurements.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import json
import os
import statistics
import subprocess
import sys
import time
import tkinter as tk

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

RESULTS = {}


def cpu_times():
    k32 = ctypes.windll.kernel32
    creation, exit_, kernel, user = (wt.FILETIME() for _ in range(4))
    k32.GetProcessTimes(k32.GetCurrentProcess(), ctypes.byref(creation),
                        ctypes.byref(exit_), ctypes.byref(kernel), ctypes.byref(user))

    def ft(f):
        return (f.dwHighDateTime << 32) + f.dwLowDateTime
    return ft(kernel) + ft(user)          # 100 ns units


def memory_mb():
    out = subprocess.run(["tasklist", "/FI", f"PID eq {os.getpid()}", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True)
    try:
        field = out.stdout.strip().splitlines()[0].split('","')[4]
        return float(field.replace(" K", "").replace(",", "").replace('"', "")) / 1024
    except Exception:
        return -1.0


def main():
    import tracemalloc
    from easyrec import config as config_mod
    from easyrec.app import EasyRecordApp

    tmp = os.path.join(HERE, "reports", ".perf_cfg.json")
    config_mod.config_path = lambda: tmp

    t0 = time.perf_counter()
    root = tk.Tk()
    root.withdraw()
    app = EasyRecordApp(root)
    root.update()
    RESULTS["startup_s"] = round(time.perf_counter() - t0, 3)

    # ---- UI tick cost (the 250 ms poll handler)
    samples = []
    for _ in range(100):
        start = time.perf_counter()
        app._render(app.recorder.snapshot())
        root.update()
        samples.append((time.perf_counter() - start) * 1000)
    RESULTS["tick_ms_avg"] = round(statistics.mean(samples), 2)
    RESULTS["tick_ms_p95"] = round(sorted(samples)[int(len(samples) * 0.95)], 2)
    RESULTS["tick_ms_max"] = round(max(samples), 2)

    # ---- render handler alone (no Tk event loop)
    render_only = []
    for _ in range(100):
        start = time.perf_counter()
        app._render(app.recorder.snapshot())
        render_only.append((time.perf_counter() - start) * 1000)
    RESULTS["render_ms_avg"] = round(statistics.mean(render_only), 2)
    RESULTS["render_ms_p95"] = round(sorted(render_only)[int(len(render_only) * 0.95)], 2)

    # ---- meter redraw alone
    meter_samples = []
    for value in range(0, 100, 2):
        start = time.perf_counter()
        app.meter.set_level(value, "none")
        root.update()
        meter_samples.append((time.perf_counter() - start) * 1000)
    RESULTS["meter_redraw_ms_avg"] = round(statistics.mean(meter_samples), 2)

    # ---- theme switch
    t = time.perf_counter()
    app.set_theme("night")
    root.update()
    RESULTS["theme_switch_ms"] = round((time.perf_counter() - t) * 1000, 1)

    # ---- language switch (full RTL rebuild)
    t = time.perf_counter()
    app.set_lang("en")
    root.update()
    RESULTS["lang_switch_ms"] = round((time.perf_counter() - t) * 1000, 1)
    app.set_lang("ar")
    app.set_theme("day")
    root.update()

    # ---- idle CPU over 5 s
    before = cpu_times()
    wall = time.perf_counter()
    while time.perf_counter() - wall < 5.0:
        root.update()
        time.sleep(0.02)
    elapsed_wall = time.perf_counter() - wall
    used = (cpu_times() - before) / 1e7            # seconds of CPU
    RESULTS["idle_cpu_pct"] = round(100.0 * used / elapsed_wall, 2)

    RESULTS["rss_mb"] = round(memory_mb(), 1)
    RESULTS["widgets"] = len(app.widgets)

    root.destroy()
    os.path.exists(tmp) and os.remove(tmp)

    out = os.path.join(HERE, "reports", "perf.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(RESULTS, fh, ensure_ascii=False, indent=2)
    for key, value in RESULTS.items():
        print(f"{key:>22}: {value}")
    print("written:", out)


if __name__ == "__main__":
    main()
