# -*- coding: utf-8 -*-
"""Bundled IBM Plex font registration.

The TTFs ship next to the app (``assets/fonts``) and are registered *privately*
for the current process only, so the machine's installed fonts are never
touched and the app looks identical on a clean Windows box.
"""

from __future__ import annotations

import os
from typing import Dict, List

from .config import asset_path

# FR_PRIVATE: font is visible to this process only.
FR_PRIVATE = 0x10
_loaded: List[str] = []

WANTED = {
    "sans_ar": ["IBMPlexSansArabic-Regular.ttf", "IBMPlexSansArabic-Medium.ttf",
                "IBMPlexSansArabic-SemiBold.ttf", "IBMPlexSansArabic-Bold.ttf"],
    "sans": ["IBMPlexSans-Regular.ttf", "IBMPlexSans-Medium.ttf",
             "IBMPlexSans-SemiBold.ttf", "IBMPlexSans-Bold.ttf"],
    "mono": ["IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf",
             "IBMPlexMono-SemiBold.ttf"],
}


def font_files() -> List[str]:
    out: List[str] = []
    for names in WANTED.values():
        for name in names:
            path = asset_path("fonts", name)
            if os.path.exists(path):
                out.append(path)
    return out


def register() -> int:
    """Register every bundled TTF for this process; returns how many loaded."""
    if _loaded:
        return len(_loaded)
    try:
        import ctypes

        gdi32 = ctypes.WinDLL("gdi32")
        add = gdi32.AddFontResourceExW
        add.argtypes = [ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p]
        add.restype = ctypes.c_int
    except Exception:
        return 0

    count = 0
    for path in font_files():
        try:
            if add(path, FR_PRIVATE, 0) > 0:
                _loaded.append(path)
                count += 1
        except Exception:
            continue
    return count


def available_families(root=None) -> set:
    """Families visible to Tk right now (registered + installed)."""
    try:
        from tkinter import font as tkfont
        return {f.strip() for f in tkfont.families(root)}
    except Exception:
        return set()


def resolve(root, logger=print) -> Dict[str, str]:
    """Return the best available family for each role and log any fallback."""
    registered = register()
    families = available_families(root)

    def pick(stack, label):
        for name in stack:
            if name in families:
                return name
        logger(f"[fonts] {label}: IBM Plex not available, falling back")
        return stack[-1]

    body = pick(("IBM Plex Sans Arabic", "IBM Plex Sans", "Segoe UI"), "body")
    mono = pick(("IBM Plex Mono", "Consolas", "Courier New"), "mono")
    logger(f"[fonts] registered={registered} families_visible={len(families)} "
           f"body={body!r} mono={mono!r}")
    return {"body": body, "mono": mono, "registered": registered}
