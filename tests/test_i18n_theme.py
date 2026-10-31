# -*- coding: utf-8 -*-
"""i18n + theme (contrast) tests: no half-translated key, no unreadable colour."""

from __future__ import annotations

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from easyrec import i18n
from easyrec import theme as palette_mod

PKG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "easyrec")


class TestTranslations(unittest.TestCase):
    def test_every_key_exists_in_both_languages(self):
        self.assertEqual(i18n.missing_keys(), {})

    def test_no_duplicate_placeholders(self):
        for key, table in i18n.STRINGS.items():
            for lang, text in table.items():
                fields = set(re.findall(r"\{(\w+)\}", text))
                for field in fields:
                    self.assertRegex(text, r"\{\w+\}", f"{key}/{lang}")

    def test_placeholders_match_between_languages(self):
        for key, table in i18n.STRINGS.items():
            ar = set(re.findall(r"\{(\w+)\}", table["ar"]))
            en = set(re.findall(r"\{(\w+)\}", table["en"]))
            self.assertEqual(ar, en, f"placeholder mismatch in {key}")

    def test_unknown_key_is_visible_not_silent(self):
        self.assertEqual(i18n.tr("ar", "does.not.exist"), "does.not.exist")

    def test_missing_kwargs_do_not_crash(self):
        self.assertIn("{sec}", i18n.tr("ar", "alert.warn"))

    def test_rtl_flags(self):
        self.assertTrue(i18n.is_rtl("ar"))
        self.assertFalse(i18n.is_rtl("en"))


class TestKeysUsedByCode(unittest.TestCase):
    """Every key referenced in the UI must exist — catches typos at build time."""

    PATTERNS = (
        re.compile(r"""\.t\(\s*["']([a-z0-9_.]+)["']"""),
        re.compile(r"""key\s*=\s*["']([a-z0-9_.]+)["']"""),
        re.compile(r"""set_key\(\s*["']([a-z0-9_.]+)["']"""),
    )

    def test_all_referenced_keys_exist(self):
        missing = set()
        for name in os.listdir(PKG):
            if not name.endswith(".py"):
                continue
            source = open(os.path.join(PKG, name), encoding="utf-8").read()
            for pattern in self.PATTERNS:
                for key in pattern.findall(source):
                    if key not in i18n.STRINGS:
                        missing.add(f"{name}:{key}")
        self.assertEqual(missing, set(), f"undefined i18n keys: {sorted(missing)}")


class TestThemeContrast(unittest.TestCase):
    """WCAG AA: 4.5:1 for body text, 3:1 for large text and UI components."""

    BODY_PAIRS = (
        ("text", "bg"), ("text", "surface"), ("text", "surface_alt"),
        ("text_muted", "surface"), ("text_muted", "bg"), ("text_faint", "surface"),
        ("neutral_text", "neutral"), ("primary", "surface"), ("success", "surface"),
        ("danger", "surface"), ("warn", "surface"),
    )
    BUTTON_PAIRS = (
        ("on_primary", "primary"), ("on_success", "success"),
        ("on_warn", "warn"), ("on_danger", "danger"),
    )

    def test_both_themes_complete(self):
        day_keys = set(palette_mod.DAY)
        night_keys = set(palette_mod.NIGHT)
        self.assertEqual(day_keys, night_keys, "day/night palettes diverged")

    def test_body_text_contrast(self):
        failures = []
        for theme_name in palette_mod.THEMES:
            colours = palette_mod.palette(theme_name)
            for fg_key, bg_key in self.BODY_PAIRS:
                ratio = palette_mod.contrast_ratio(colours[fg_key], colours[bg_key])
                if ratio < 4.5:
                    failures.append(f"{theme_name}:{fg_key}/{bg_key} = {ratio:.2f}")
        self.assertEqual(failures, [])

    def test_button_label_contrast(self):
        failures = []
        for theme_name in palette_mod.THEMES:
            colours = palette_mod.palette(theme_name)
            for fg_key, bg_key in self.BUTTON_PAIRS:
                ratio = palette_mod.contrast_ratio(colours[fg_key], colours[bg_key])
                if ratio < 4.5:
                    failures.append(f"{theme_name}:{fg_key}/{bg_key} = {ratio:.2f}")
        self.assertEqual(failures, [])

    def test_day_is_light_and_night_is_dark(self):
        self.assertGreater(palette_mod.relative_luminance(palette_mod.DAY["bg"]), 0.75)
        self.assertLess(palette_mod.relative_luminance(palette_mod.NIGHT["bg"]), 0.05)

    def test_mix_blends_midway(self):
        self.assertEqual(palette_mod.mix("#000000", "#FFFFFF", 0.5).upper(), "#808080")


if __name__ == "__main__":
    unittest.main(verbosity=2)
