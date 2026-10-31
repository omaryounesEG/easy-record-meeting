# -*- coding: utf-8 -*-
"""Shared fixtures: a fake loopback device so the engine can be tested without
touching real hardware, plus helpers for temporary folders."""

from __future__ import annotations

import math
import os
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from easyrec import engine  # noqa: E402


class FakeCapture:
    """Context manager mimicking ``soundcard``'s loopback recorder."""

    def __init__(self, amplitude: float = 0.30, freq: float = 440.0,
                 fail_after: int | None = None, block: float | None = None):
        self.amplitude = amplitude
        self.freq = freq
        self.fail_after = fail_after
        # a real loopback read blocks for exactly the chunk duration
        self.block = block
        self.reads = 0
        self.phase = 0.0
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.closed = True
        return False

    def record(self, numframes: int):
        if self.fail_after is not None and self.reads >= self.fail_after:
            raise RuntimeError("device unplugged")
        self.reads += 1
        if self.block is None:
            import time
            time.sleep(numframes / engine.SAMPLE_RATE)
        elif self.block:
            import time
            time.sleep(self.block)
        t = np.arange(numframes, dtype=np.float64) / engine.SAMPLE_RATE + self.phase
        self.phase += numframes / engine.SAMPLE_RATE
        mono = self.amplitude * np.sin(2 * math.pi * self.freq * t)
        return np.stack([mono, mono], axis=1)


class FakeDevice:
    def __init__(self, **kwargs):
        self.name = "Fake Loopback Speaker"
        self.kwargs = kwargs
        self.capture: FakeCapture | None = None

    def recorder(self, samplerate: int, channels: int):
        self.capture = FakeCapture(**self.kwargs)
        return self.capture


def temp_dir(prefix: str = "easyrec_test_") -> str:
    return tempfile.mkdtemp(prefix=prefix)
