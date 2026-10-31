# -*- coding: utf-8 -*-
"""Headless-ish UI smoke test: builds the window, switches theme/language,
captures screenshots for visual review and reports any exception."""
from __future__ import annotations

import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import tkinter as tk

SHOTS = os.path.join(HERE, "reports", "shots")
os.makedirs(SHOTS, exist_ok=True)


def grab(root, name):
    try:
        from PIL import ImageGrab
    except Exception as exc:
        print("no PIL:", exc)
        return
    root.update_idletasks()
    root.update()
    x, y = root.winfo_rootx(), root.winfo_rooty()
    w, h = root.winfo_width(), root.winfo_height()
    img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    path = os.path.join(SHOTS, name)
    img.save(path)
    print("SHOT", path, img.size)


def main():
    from easyrec.app import EasyRecordApp

    root = tk.Tk()
    app = EasyRecordApp(root)
    root.update_idletasks()
    root.update()
    for _ in range(12):
        root.update()
        time.sleep(0.05)
    print("built ok; widgets:", len(app.widgets))
    grab(root, "01_day_ar.png")

    app.set_theme("night")
    for _ in range(8):
        root.update(); time.sleep(0.05)
    grab(root, "02_night_ar.png")

    app.set_lang("en")
    for _ in range(12):
        root.update(); time.sleep(0.05)
    grab(root, "03_night_en.png")

    app.set_theme("day")
    for _ in range(8):
        root.update(); time.sleep(0.05)
    grab(root, "04_day_en.png")

    print("widgets after rebuild:", len(app.widgets))
    print("fonts:", app.fonts)
    root.destroy()
    print("SMOKE OK")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
