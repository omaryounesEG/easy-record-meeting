# -*- coding: utf-8 -*-
"""Performance budget tests: startup, poll tick cost, theme/lang switch, memory.

Budgets are deliberately generous (CI machines are noisy) but still tight enough
to catch a redraw storm or a blocking call on the UI thread.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import os
import statistics
import sys
import tempfile
import time
import tkinter as tk
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from easyrec import config as config_mod

REPORT = {}


def rss_mb() -> float:
    try:
        class PMC(ctypes.Structure):
            _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]
        info = PMC()
        info.cb = ctypes.sizeof(PMC)
        ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(info), info.cb)
        return info.WorkingSetSize / (1024 * 1024)
    except Exception:
        return -1.0


class TestPerformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp(prefix="easyrec_perf_")
        cls._old = config_mod.config_path
        config_mod.config_path = lambda: os.path.join(cls._tmp, "config.json")

        from easyrec.app import EasyRecordApp
        started = time.perf_counter()
        cls.root = tk.Tk()
        cls.root.withdraw()
        cls.app = EasyRecordApp(cls.root)
        cls.root.update()
        cls.startup = time.perf_counter() - started
        cls.baseline_rss = rss_mb()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()
        config_mod.config_path = cls._old

    def test_startup_budget(self):
        REPORT["startup_s"] = round(self.startup, 3)
        self.assertLess(self.startup, 4.0, "startup slower than 4 s")

    def test_poll_tick_cost(self):
        samples = []
        for _ in range(40):
            t0 = time.perf_counter()
            self.app._render(self.app.recorder.snapshot())
            self.root.update()
            samples.append((time.perf_counter() - t0) * 1000)
        avg = statistics.mean(samples)
        REPORT["tick_ms_avg"] = round(avg, 2)
        REPORT["tick_ms_p95"] = round(sorted(samples)[int(len(samples) * 0.95)], 2)
        self.assertLess(avg, 25.0, f"UI tick too slow: {avg:.1f} ms")
        self.assertLess(max(samples), 120.0)

    def test_theme_switch_cost(self):
        t0 = time.perf_counter()
        self.app.set_theme("night")
        self.root.update()
        elapsed = time.perf_counter() - t0
        REPORT["theme_switch_ms"] = round(elapsed * 1000, 1)
        self.app.set_theme("day")
        self.root.update()
        self.assertLess(elapsed, 1.5, f"theme switch too slow: {elapsed:.2f}s")

    def test_language_switch_cost(self):
        t0 = time.perf_counter()
        self.app.set_lang("en")
        self.root.update()
        elapsed = time.perf_counter() - t0
        REPORT["lang_switch_ms"] = round(elapsed * 1000, 1)
        self.app.set_lang("ar")
        self.root.update()
        self.assertLess(elapsed, 3.0, f"language switch too slow: {elapsed:.2f}s")

    def test_memory_budget(self):
        REPORT["rss_mb"] = round(rss_mb(), 1)
        self.assertLess(REPORT["rss_mb"], 320.0)

    def test_no_thread_leak_on_theme_switch(self):
        import threading
        before = threading.active_count()
        for _ in range(5):
            self.app.set_theme("night")
            self.app.set_theme("day")
            self.root.update()
        time.sleep(0.3)
        self.assertLessEqual(threading.active_count(), before + 1)

    def test_report(self):
        print("\nPERF REPORT:", REPORT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
