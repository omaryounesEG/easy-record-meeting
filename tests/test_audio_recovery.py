# -*- coding: utf-8 -*-
"""The reported defect: video keeps recording while the audio track goes dead.

A USB/Bluetooth endpoint that sleeps keeps the WASAPI stream open but delivers
pure silence, so the MP4 grows with no sound.  These tests pin the recovery
behaviour and the "never record a silent picture" rule.
"""
from __future__ import annotations

import math
import os
import shutil
import time
import unittest

import numpy as np

from easyrec import engine
from tests.support import temp_dir

CHUNK = 441                      # 10 ms of audio at 44.1 kHz


class _Capture:
    """Fake recorder: real tone, then silence from a given read onward."""

    def __init__(self, stream_index: int, silent_from: int | None):
        self.stream_index = stream_index
        self.silent_from = silent_from
        self.reads = 0
        self.phase = 0.0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def record(self, numframes: int):
        self.reads += 1
        if self.silent_from is not None and self.reads >= self.silent_from:
            return np.zeros((numframes, 2))
        t = np.arange(numframes, dtype=np.float64) / engine.SAMPLE_RATE + self.phase
        self.phase += numframes / engine.SAMPLE_RATE
        mono = 0.4 * np.sin(2 * math.pi * 440.0 * t)
        return np.stack([mono, mono], axis=1)


class SleepingDevice:
    """First stream goes silent (simulating a sleeping endpoint), later ones work."""

    name = "Sleeping Loopback"

    def __init__(self, silent_from: int | None = 4):
        self.silent_from = silent_from
        self.streams = 0

    def recorder(self, samplerate: int, channels: int):
        self.streams += 1
        silent_from = self.silent_from if self.streams == 1 else None
        return _Capture(self.streams, silent_from)


class BrokenDevice:
    name = "Broken Loopback"

    def __init__(self):
        self.streams = 0

    def recorder(self, samplerate: int, channels: int):
        self.streams += 1
        raise RuntimeError("device unplugged")


class TestAudioRecovery(unittest.TestCase):
    def setUp(self):
        self._chunk = engine.CHUNK_FRAMES
        self._stall = engine.AUDIO_STALL_SECONDS
        self._list = engine.list_devices
        engine.list_devices = lambda: []          # never touch the real hardware
        engine.CHUNK_FRAMES = CHUNK
        engine.AUDIO_STALL_SECONDS = 0.05          # 5 silent chunks
        self.dir = temp_dir("recover_")

    def tearDown(self):
        engine.CHUNK_FRAMES = self._chunk
        engine.AUDIO_STALL_SECONDS = self._stall
        engine.list_devices = self._list
        if getattr(self, "rec", None) is not None:
            try:
                self.rec.stop()
            except Exception:
                pass
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_sleeping_device_is_reopened_and_audio_returns(self):
        """Silence after real sound restarts the stream instead of losing audio."""
        device = SleepingDevice()
        self.rec = rec = engine.Recorder()
        rec.start(mode="audio", directory=self.dir, device=device)

        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline and device.streams < 2:
            time.sleep(0.02)
        self.assertGreaterEqual(device.streams, 2, "the stream was never reopened")
        self.assertIn("reconnect", rec.snapshot().notice.lower())

        # audio must be flowing again through the fresh stream
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline and rec.snapshot().level < 50:
            time.sleep(0.02)
        self.assertGreaterEqual(rec.snapshot().level, 50, "audio did not come back")
        self.assertEqual(rec.snapshot().status, "recording",
                         "recovery must not end the recording")

        result = rec.stop()
        self.assertEqual(result.status, "done")
        self.assertGreater(os.path.getsize(result.output_path), 1024,
                           "the mp3 holds audio from before and after the restart")

    def test_endless_silence_gives_up_after_the_retry_budget(self):
        """A device that never returns audio ends in a visible error, not silence."""
        self.rec = rec = engine.Recorder()
        rec.start(mode="audio", directory=self.dir, device=BrokenDevice())
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline and rec.snapshot().status not in ("error", "done"):
            time.sleep(0.05)
        snap = rec.snapshot()
        self.assertEqual(snap.status, "error")
        self.assertTrue(snap.error)

    def test_audio_failure_kills_the_video_instead_of_recording_a_silent_picture(self):
        """The reported symptom: picture kept growing after the sound died."""
        killed = {"called": False}

        def fake_kill():
            killed["called"] = True

        original = engine.Recorder._kill_video
        engine.Recorder._kill_video = lambda self: fake_kill()
        try:
            self.rec = rec = engine.Recorder()
            rec.start(mode="audio", directory=self.dir, device=BrokenDevice())
            deadline = time.monotonic() + 10.0
            while time.monotonic() < deadline and rec.snapshot().status not in ("error", "done"):
                time.sleep(0.05)
        finally:
            engine.Recorder._kill_video = original
        self.assertTrue(killed["called"], "the video process would have kept running")

    def test_stop_after_error_still_cleans_up(self):
        """stop() used to return early on error and leave ffmpeg writing to disk."""
        self.rec = rec = engine.Recorder()
        rec.start(mode="audio", directory=self.dir, device=BrokenDevice())
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline and rec.snapshot().status not in ("error", "done"):
            time.sleep(0.05)
        self.assertEqual(rec.snapshot().status, "error")
        snap = rec.stop()                     # must not raise and must not hang
        self.assertEqual(snap.status, "error")
        self.assertFalse(snap.is_active, "stop() must leave no active state behind")


if __name__ == "__main__":
    unittest.main()
