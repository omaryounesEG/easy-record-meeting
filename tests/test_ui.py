# -*- coding: utf-8 -*-
"""UI tests: rounded widgets behave, theme/language switch is lossless."""

from __future__ import annotations

import os
import sys
import tempfile
import tkinter as tk
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from easyrec import config as config_mod
from easyrec import theme as theme_mod
from easyrec.widgets import Meter, RoundButton, Segmented, TLabel, ToggleSwitch


class AppFixture(unittest.TestCase):
    """One Tk root + one app for the whole class (Tk dislikes repeated roots)."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp(prefix="easyrec_cfg_")
        cls._old_cfg = config_mod.config_path
        config_mod.config_path = lambda: os.path.join(cls._tmp, "config.json")

        cls.root = tk.Tk()
        cls.root.withdraw()
        from easyrec.app import EasyRecordApp
        cls.app = EasyRecordApp(cls.root)
        cls.root.update()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass
        config_mod.config_path = cls._old_cfg


class TestWidgets(AppFixture):
    def test_round_button_click(self):
        calls = []
        btn = RoundButton(self.root, self.app, text="Go", tone="primary",
                          command=lambda: calls.append(1))
        btn.pack()
        self.root.update()
        btn._on_press()
        btn._on_release()
        self.assertEqual(calls, [1])

    def test_round_button_disabled_ignores_click(self):
        calls = []
        btn = RoundButton(self.root, self.app, text="No", command=lambda: calls.append(1))
        btn.set_enabled(False)
        btn._on_release()
        self.assertEqual(calls, [])

    def test_round_button_hover_changes_fill(self):
        btn = RoundButton(self.root, self.app, text="Hover", tone="primary")
        btn.pack()
        self.root.update()
        normal = btn.itemcget(1, "fill")
        btn._on_enter()
        hovered = btn.itemcget(1, "fill")
        self.assertNotEqual(normal, hovered)

    def test_toggle_switch_flips_variable(self):
        var = tk.BooleanVar(value=False)
        switch = ToggleSwitch(self.root, self.app, var)
        switch._toggle()
        self.assertTrue(var.get())

    def test_segmented_selects_option(self):
        seen = []
        seg = Segmented(self.root, self.app, options=[("a", "theme.day"), ("b", "theme.night")],
                        value="a", command=seen.append)
        seg.pack()
        self.root.update()
        seg.set_value("b")
        self.assertEqual(seg.value, "b")
        self.assertEqual(seen, ["b"])

    def test_meter_paints_level_in_place(self):
        """The meter reuses its 34 items (fast path), so check colours, not count."""
        meter = Meter(self.root, self.app)
        meter.pack(fill="x")
        self.root.update()
        meter.set_level(0)
        track = self.app.colors["meter_track"]
        self.assertTrue(all(meter.itemcget(i, "fill") == track for i in meter.find_all()))
        meter.set_level(80)
        lit = [i for i in meter.find_all() if meter.itemcget(i, "fill") != track]
        self.assertGreaterEqual(len(lit), 25)
        meter.set_level(0)
        self.assertTrue(all(meter.itemcget(i, "fill") == track for i in meter.find_all()))

    def test_labels_use_plex_font(self):
        label = TLabel(self.root, self.app, key="app.title", kind="strong")
        self.assertIn("Plex", label.cget("font"))


class TestThemeSwitch(AppFixture):
    def test_default_theme_is_day(self):
        self.assertEqual(self.app.theme_name, "day")
        self.assertEqual(self.root.cget("bg"), theme_mod.DAY["bg"])

    def test_switch_to_night_repaints_every_widget(self):
        self.app.set_theme("night")
        self.root.update()
        self.assertEqual(self.root.cget("bg"), theme_mod.NIGHT["bg"])
        failures = []
        for widget in self.app.widgets:
            try:
                widget.apply_theme()
            except Exception as exc:
                failures.append(f"{type(widget).__name__}: {exc}")
        self.assertEqual(failures, [])
        self.app.set_theme("day")
        self.root.update()

    def test_theme_persists_to_config(self):
        self.app.set_theme("night")
        saved = config_mod.Config.load()
        self.assertEqual(saved.theme, "night")
        self.app.set_theme("day")


class TestLanguageSwitch(AppFixture):
    def test_switch_to_english_flips_direction(self):
        self.app.set_lang("en")
        self.root.update()
        self.assertFalse(self.app.rtl)
        self.assertIn("Easy Record Meeting", self.root.title())
        self.assertNotEqual(self.app.status_chip.cget("width"), "")

    def test_switch_back_to_arabic(self):
        self.app.set_lang("ar")
        self.root.update()
        self.assertTrue(self.app.rtl)
        self.assertIn("مسجل الاجتماعات", self.root.title())

    def test_layout_survives_rebuild(self):
        before = len(self.app.widgets)
        self.app.set_lang("en")
        self.root.update()
        self.app.set_lang("ar")
        self.root.update()
        self.assertAlmostEqual(len(self.app.widgets), before, delta=6)

    def test_no_destroyed_widget_in_registry(self):
        self.app.set_lang("en")
        self.root.update()
        dead = [w for w in self.app.widgets if not w.winfo_exists()]
        self.assertEqual(dead, [])


class TestRecordingControls(AppFixture):
    def test_controls_start_disabled_correctly(self):
        self.app._render(self.app.recorder.snapshot())
        self.assertTrue(self.app.start_btn.enabled)
        self.assertFalse(self.app.pause_btn.enabled)
        self.assertFalse(self.app.stop_btn.enabled)

    def test_start_button_follows_mode(self):
        self.app.mode_var.set("audio")
        self.app._on_mode_change()
        self.assertEqual(self.app.start_btn.key, "btn.start.audio")
        self.app.mode_var.set("video")
        self.app._on_mode_change()
        self.assertEqual(self.app.start_btn.key, "btn.start.video")


if __name__ == "__main__":
    unittest.main(verbosity=2)
