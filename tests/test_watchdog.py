# -*- coding: utf-8 -*-
"""Watchdogs: a wedged audio read or a dead ffmpeg must not end the recording.

Merged behaviour: the NEW build's endless reconnect loop is combined with the
segment machinery, so a stream that never returns is abandoned and a fresh
segment starts instead of freezing the recording.
"""
from __future__ import annotations

import os
import shutil
import sys
import threading
import time
import unittest
from unittest import mock

import numpy as np

from easyrec import engine
from tests.support import temp_dir

CHUNK = 441


class _Wedged:
    """A recorder whose read() never returns until released (WASAPI deadlock)."""

    def __init__(self, release: threading.Event):
        self.release = release
        self.reads = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def record(self, numframes: int):
        self.reads += 1
        self.release.wait(30)
        return np.zeros((numframes, 2))


class WedgedDevice:
    name = "Wedged Loopback"

    def __init__(self):
        self.release = threading.Event()
        self.streams = 0

    def recorder(self, samplerate: int, channels: int):
        self.streams += 1
        return _Wedged(self.release)


class ToneDevice:
    """Always returns a tone (used after a roll)."""

    name = "Tone Loopback"

    def recorder(self, samplerate: int, channels: int):
        class _Cap:
            phase = 0.0

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def record(self, numframes):
                t = np.arange(numframes, dtype=np.float64) / engine.SAMPLE_RATE + _Cap.phase
                _Cap.phase += numframes / engine.SAMPLE_RATE
                mono = 0.4 * np.sin(2 * 3.141592653589793 * 440.0 * t)
                return np.stack([mono, mono], axis=1)
        return _Cap()


class _DeadProc:
    """Stands in for an ffmpeg process that died."""

    stdin = None

    def poll(self):
        return 1

    def wait(self, timeout=None):
        return 1

    def terminate(self):
        pass

    def kill(self):
        pass


class TestWatchdog(unittest.TestCase):
    def setUp(self):
        self._chunk = engine.CHUNK_FRAMES
        self._audio_stall = engine.AUDIO_HARD_STALL
        self._video_stall = engine.VIDEO_HARD_STALL
        self._list = engine.list_devices
        engine.CHUNK_FRAMES = CHUNK
        engine.AUDIO_HARD_STALL = 0.4
        engine.VIDEO_HARD_STALL = 0.4
        engine.list_devices = lambda: []
        self.dir = temp_dir("watchdog_")
        self.rec = None

    def tearDown(self):
        if self.rec is not None:
            try:
                self.rec.cancel()
            except Exception:
                pass
        engine.CHUNK_FRAMES = self._chunk
        engine.AUDIO_HARD_STALL = self._audio_stall
        engine.VIDEO_HARD_STALL = self._video_stall
        engine.list_devices = self._list
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_wedged_audio_read_rolls_a_new_segment(self):
        """A read that never returns used to freeze the audio for the rest of the call."""
        device = WedgedDevice()
        self.rec = rec = engine.Recorder()
        rec.start(mode="audio", directory=self.dir, device=device)

        deadline = time.monotonic() + 6.0
        while time.monotonic() < deadline and len(rec._segments) < 2:
            time.sleep(0.05)

        self.assertGreaterEqual(len(rec._segments), 2, "the watchdog never rolled a segment")
        self.assertEqual(rec.snapshot().status, "recording", "the recording must survive")
        self.assertTrue(rec.snapshot().notice)
        device.release.set()          # unblock the abandoned reader so it can exit

    def test_dead_ffmpeg_rolls_a_new_segment(self):
        """If ffmpeg dies mid-call the screen capture must resume, not silently stop."""
        self.rec = rec = engine.Recorder()
        with mock.patch.object(engine.Recorder, "_spawn_video",
                               lambda self, target, progress=None: setattr(self, "_video", _DeadProc())):
            rec.start(mode="video", directory=self.dir, device=ToneDevice())
            deadline = time.monotonic() + 6.0
            while time.monotonic() < deadline and len(rec._segments) < 2:
                time.sleep(0.05)

        self.assertGreaterEqual(len(rec._segments), 2, "a dead ffmpeg was not restarted")
        self.assertEqual(rec.snapshot().status, "recording")

    def test_reconnect_matches_the_endpoint_fuzzily(self):
        """Ported from NEW: the endpoint name gains a changing index prefix."""
        target = mock.Mock()
        target.name = "Speakers (2- Logi USB Headset H340)"
        target.isloopback = True
        other = mock.Mock()
        other.name = "Microphone (USB)"
        other.isloopback = False
        stub = mock.Mock()
        stub.all_microphones.return_value = [other, target]

        self.rec = rec = engine.Recorder()
        rec._device_name = "Speakers (3- Logi USB Headset H340)"
        with mock.patch.dict(sys.modules, {"soundcard": stub}):
            found = rec._reconnect_device()
        self.assertIs(found, target, "the loopback endpoint was not matched by name")


if __name__ == "__main__":
    unittest.main()
