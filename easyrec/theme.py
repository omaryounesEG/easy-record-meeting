# -*- coding: utf-8 -*-
"""Design tokens for the day (light) and night (dark) themes.

The palette is deliberately low-chroma ("soft") per the brand brief: neutral
surfaces, one blue accent, calm green for success and a single warm red for
danger.  ``contrast_ratio`` is used by the tests to guarantee readable text in
both modes (WCAG AA: >= 4.5 for body text, >= 3.0 for large text).
"""

from __future__ import annotations

from typing import Dict

THEMES = ("day", "night")

DAY: Dict[str, str] = {
    "name": "day",
    "bg": "#F4F6FB",
    "surface": "#FFFFFF",
    "surface_alt": "#EDF1F9",
    "surface_sunken": "#E4EAF5",
    "border": "#DCE3F0",
    "border_strong": "#C4D0E4",
    "text": "#101B2D",
    "text_muted": "#4F6178",
    "text_faint": "#63758D",
    "inverse": "#FFFFFF",
    "primary": "#2B63E8",
    "primary_hover": "#1D53D6",
    "primary_press": "#1745B0",
    "primary_soft": "#E6EDFF",
    "success": "#077A55",
    "success_hover": "#066848",
    "success_press": "#04533A",
    "success_soft": "#DFF6EC",
    "warn": "#A96400",
    "warn_hover": "#8F5400",
    "warn_press": "#774600",
    "warn_soft": "#FDF0DC",
    "danger": "#C93A3A",
    "danger_hover": "#AF2F2F",
    "danger_press": "#932626",
    "danger_soft": "#FDE7E7",
    "on_primary": "#FFFFFF",
    "on_success": "#FFFFFF",
    "on_warn": "#FFFFFF",
    "on_danger": "#FFFFFF",
    "neutral": "#E7ECF6",
    "neutral_hover": "#DAE2F1",
    "neutral_press": "#CBD6EA",
    "neutral_text": "#20304A",
    "disabled_bg": "#EAEEF6",
    "disabled_text": "#A2AFC4",
    "meter_track": "#E4EAF5",
    "track": "#D7E0EF",
    "shadow": "#DCE4F2",
    "chip": "#EDF1F9",
}

NIGHT: Dict[str, str] = {
    "name": "night",
    "bg": "#0C1424",
    "surface": "#131E31",
    "surface_alt": "#182741",
    "surface_sunken": "#0F1929",
    "border": "#25354F",
    "border_strong": "#34486A",
    "text": "#EAF0FA",
    "text_muted": "#A5B6CE",
    "text_faint": "#93A5BF",
    "inverse": "#0C1424",
    "primary": "#6E9BFF",
    "primary_hover": "#88AEFF",
    "primary_press": "#5686EE",
    "primary_soft": "#1B2A45",
    "success": "#34D399",
    "success_hover": "#4DE0A8",
    "success_press": "#26B782",
    "success_soft": "#122F27",
    "warn": "#F0B45A",
    "warn_hover": "#FFC476",
    "warn_press": "#D99A3E",
    "warn_soft": "#33270F",
    "danger": "#FF8080",
    "danger_hover": "#FF9A9A",
    "danger_press": "#E46262",
    "danger_soft": "#3A1B1B",
    "on_primary": "#0B1526",
    "on_success": "#062018",
    "on_warn": "#2A1D06",
    "on_danger": "#2A0B0B",
    "neutral": "#22314A",
    "neutral_hover": "#2C3E5C",
    "neutral_press": "#374C70",
    "neutral_text": "#DCE6F5",
    "disabled_bg": "#1A2639",
    "disabled_text": "#5F7191",
    "meter_track": "#1C2A42",
    "track": "#22314A",
    "shadow": "#0A1120",
    "chip": "#1A2740",
}

PALETTES: Dict[str, Dict[str, str]] = {"day": DAY, "night": NIGHT}

FONT_STACK = ("IBM Plex Sans Arabic", "IBM Plex Sans", "Segoe UI")
MONO_STACK = ("IBM Plex Mono", "Consolas", "Courier New")


def palette(name: str) -> Dict[str, str]:
    return PALETTES.get(name, DAY)


# --------------------------------------------------------------------- colour maths
def _srgb_to_linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return 0.2126 * _srgb_to_linear(r) + 0.7152 * _srgb_to_linear(g) + 0.0722 * _srgb_to_linear(b)


def contrast_ratio(fg: str, bg: str) -> float:
    l1, l2 = relative_luminance(fg), relative_luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def mix(color_a: str, color_b: str, weight: float) -> str:
    """Blend two hex colours; ``weight`` is the share of ``color_a`` (0..1)."""
    weight = max(0.0, min(1.0, weight))
    a = color_a.lstrip("#")
    b = color_b.lstrip("#")
    out = []
    for i in (0, 2, 4):
        ca = int(a[i:i + 2], 16)
        cb = int(b[i:i + 2], 16)
        out.append(int(round(ca * weight + cb * (1 - weight))))
    return "#%02X%02X%02X" % tuple(out)
