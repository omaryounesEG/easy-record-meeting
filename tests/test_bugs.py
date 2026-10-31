# -*- coding: utf-8 -*-
"""Bug regression tests — each one pins a defect found in v1 (omar_rec_v1.py)."""

from __future__ import annotations

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from easyrec import engine
from easyrec.config import Config
from tests.support import FakeDevice, temp_dir


class TestTimestampParsing(unittest.TestCase):
    """v1 accepted any string; malformed input reached ffmpeg and failed silently."""

    def test_valid_formats(self):
        self.assertAlmostEqual(engine.parse_timestamp("01:02:03"), 3723.0)
        self.assertAlmostEqual(engine.parse_timestamp("02:30"), 150.0)
        self.assertAlmostEqual(engine.parse_timestamp("45"), 45.0)
        self.assertAlmostEqual(engine.parse_timestamp("00:00:01.500"), 1.5)

    def test_rejects_garbage(self):
        for bad in ("", "abc", "1:2:3:4", "-00:01", "::"):
            with self.assertRaises(ValueError):
                engine.parse_timestamp(bad)

    def test_duration_clamps_negative(self):
        self.assertEqual(engine.format_duration(-5), "00:00:00")
        self.assertEqual(engine.format_duration(3661), "01:01:01")


class TestConfigEncoding(unittest.TestCase):
    """v1 wrote JSON with the locale codec -> Arabic folders were never saved."""

    def test_arabic_folder_roundtrip(self):
        folder = temp_dir()
        path = os.path.join(folder, "config.json")
        cfg = Config(directory=r"D:\تسجيلات الوُرش", lang="ar", theme="night")
        self.assertTrue(cfg.save(path))
        loaded = Config.load(path)
        self.assertEqual(loaded.directory, r"D:\تسجيلات الوُرش")
        self.assertEqual(loaded.theme, "night")

    def test_raw_file_is_utf8_not_cp1252(self):
        folder = temp_dir()
        path = os.path.join(folder, "config.json")
        Config(directory=r"D:\مجلد عربي").save(path)
        raw = open(path, "rb").read()
        self.assertIn("مجلد عربي".encode("utf-8"), raw)
        raw.decode("utf-8")                     # must not raise

    def test_legacy_v1_schema_is_migrated(self):
        folder = temp_dir()
        path = os.path.join(folder, "config.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"mode": "audio", "dir": "D:\\\\DBA_Records"}')
        cfg = Config.load(path)
        self.assertEqual(cfg.mode, "audio")
        self.assertEqual(cfg.directory, r"D:\DBA_Records")
        self.assertEqual(cfg.lang, "ar")        # default for a missing key

    def test_corrupt_file_falls_back_to_defaults(self):
        folder = temp_dir()
        path = os.path.join(folder, "config.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        cfg = Config.load(path)
        self.assertEqual(cfg.mode, "video")
        self.assertEqual(cfg.lang, "ar")

    def test_atomic_save_leaves_no_temp(self):
        folder = temp_dir()
        path = os.path.join(folder, "config.json")
        Config().save(path)
        self.assertFalse(os.path.exists(path + ".tmp"))


class TestDefaultFolderFallback(unittest.TestCase):
    """v1 only defined ``self.desktop`` inside the exception branch, so any code
    path that used it after a successful D:\\DBA_Records creation crashed."""

    def test_fallback_dir_exists_and_is_absolute(self):
        from easyrec.config import default_output_dir
        path = default_output_dir()
        self.assertTrue(os.path.isabs(path))
        self.assertTrue(os.path.isdir(path))


class TestRecorderLifecycle(unittest.TestCase):
    def setUp(self):
        self.dir = temp_dir("easyrec_engine_")
        self.device = FakeDevice()
        self.recorder = engine.Recorder(ffmpeg=engine.resolve_ffmpeg())

    def tearDown(self):
        for name in os.listdir(self.dir):
            try:
                os.remove(os.path.join(self.dir, name))
            except OSError:
                pass

    def test_mp3_file_is_complete_after_stop(self):
        """v1 muxed/closed before the writer finished -> truncated tails."""
        path = self.recorder.start(mode="audio", directory=self.dir,
                                   device=self.device, name_prefix="تسجيل")
        time.sleep(1.2)
        snap = self.recorder.stop(timeout=20)
        self.assertEqual(snap.status, "done", snap.error)
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 5000)
        duration = engine.media_duration(engine.resolve_ffmpeg(), path)
        self.assertGreater(duration, 0.9, "recording lost its audio")
        self.assertLess(duration, 3.0)

    def test_no_temp_files_left_behind(self):
        self.recorder.start(mode="audio", directory=self.dir, device=self.device)
        time.sleep(0.6)
        self.recorder.stop()
        leftovers = [f for f in os.listdir(self.dir) if f.startswith(".") or f.endswith(".part")]
        self.assertEqual(leftovers, [])

    def test_level_is_measured(self):
        self.recorder.start(mode="audio", directory=self.dir, device=self.device)
        time.sleep(0.8)
        snap = self.recorder.snapshot()
        self.assertGreater(snap.level, 10.0, "signal level not measured")
        self.recorder.stop()

    def test_pause_excludes_time_and_splits_segments(self):
        self.recorder.start(mode="audio", directory=self.dir, device=self.device)
        time.sleep(0.8)
        self.recorder.pause()
        paused_for = 0.7
        time.sleep(paused_for)
        self.recorder.resume()
        time.sleep(0.6)
        snap = self.recorder.stop()
        self.assertEqual(snap.status, "done", snap.error)
        # ~1.4 s of audio, not ~2.1 s: paused time must not be counted
        self.assertLess(snap.elapsed, 1.4 + paused_for - 0.3)

    def test_device_failure_surfaces_as_error(self):
        """v1 printed the exception to the console and kept showing “recording”."""
        device = FakeDevice(fail_after=2)
        self.recorder.start(mode="audio", directory=self.dir, device=device)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if self.recorder.status == "error":
                break
            time.sleep(0.1)
        snap = self.recorder.snapshot()
        self.assertEqual(snap.status, "error")
        self.assertIn("audio device error", snap.error or "")

    def test_double_start_is_rejected(self):
        self.recorder.start(mode="audio", directory=self.dir, device=self.device)
        with self.assertRaises(engine.RecorderError):
            self.recorder.start(mode="audio", directory=self.dir, device=self.device)
        self.recorder.stop()

    def test_missing_device_is_rejected(self):
        with self.assertRaises(engine.RecorderError):
            self.recorder.start(mode="audio", directory=self.dir, device=None)

    def test_mute_alarm_flag(self):
        self.recorder.start(mode="audio", directory=self.dir, device=self.device)
        self.recorder.mute_alarm()
        self.assertTrue(self.recorder.snapshot().alarm_muted)
        self.recorder.stop()


class TestSilenceAlarm(unittest.TestCase):
    def test_warn_then_critical(self):
        folder = temp_dir("easyrec_silence_")
        device = FakeDevice(amplitude=0.0)      # pure silence
        recorder = engine.Recorder(ffmpeg=engine.resolve_ffmpeg(),
                                   warn_after=0.4, critical_after=0.9)
        recorder.start(mode="audio", directory=folder, device=device)
        time.sleep(0.7)
        self.assertEqual(recorder.snapshot().alert, "warn")
        time.sleep(0.6)
        snap = recorder.snapshot()
        self.assertEqual(snap.alert, "critical")
        self.assertGreater(snap.silence, 0.8)
        recorder.stop()

    def test_recovery_clears_alert(self):
        folder = temp_dir("easyrec_silence2_")
        recorder = engine.Recorder(ffmpeg=engine.resolve_ffmpeg(),
                                   warn_after=0.3, critical_after=5.0)
        device = FakeDevice(amplitude=0.0)
        recorder.start(mode="audio", directory=folder, device=device)
        time.sleep(0.5)
        self.assertEqual(recorder.snapshot().alert, "warn")
        recorder._last_sound = time.monotonic()      # pretend audio came back
        recorder._level = 50.0
        self.assertEqual(recorder.snapshot().alert, "none")
        recorder.stop()


class TestSafeName(unittest.TestCase):
    def test_arabic_prefix_stays_readable(self):
        name = engine.safe_name("تسجيل")
        self.assertTrue(name.startswith("تسجيل_"))
        for forbidden in '<>:"/\\|?*':
            self.assertNotIn(forbidden, name)

    def test_empty_prefix(self):
        self.assertTrue(engine.safe_name("").startswith("Recording_"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
