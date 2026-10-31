# -*- coding: utf-8 -*-
"""Produces the screenshots used in README/docs (day, night, AR, EN, dialogs)."""
from __future__ import annotations

import os
import shutil
import sys
import time
import tkinter as tk

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from PIL import ImageGrab

OUT = os.path.join(HERE, "docs", "images")
os.makedirs(OUT, exist_ok=True)


def grab_widget(win, name, pad=0):
    try:
        win.attributes("-topmost", True)
        win.lift()
    except Exception:
        pass
    for _ in range(12):
        win.update_idletasks()
        win.update()
        time.sleep(0.04)
    x, y = win.winfo_rootx() - pad, win.winfo_rooty() - pad
    w, h = win.winfo_width() + pad * 2, win.winfo_height() + pad * 2
    img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    try:
        win.attributes("-topmost", False)
    except Exception:
        pass
    path = os.path.join(OUT, name)
    img.save(path)
    print("saved", path, img.size)
    return path


def pump(root, seconds=0.5):
    end = time.time() + seconds
    while time.time() < end:
        root.update()
        time.sleep(0.03)


def main():
    from easyrec import config as config_mod
    from easyrec.app import EasyRecordApp

    cfg = config_mod.Config.load()
    cfg.lang, cfg.theme = "ar", "day"
    cfg.save()

    root = tk.Tk()
    root.withdraw()
    app = EasyRecordApp(root)
    root.deiconify()
    pump(root, 2.0)

    app.set_lang("ar")
    app.set_theme("day")
    pump(root, 0.6)
    grab_widget(root, "01_day_ar.png")

    app.set_theme("night")
    pump(root, 0.6)
    grab_widget(root, "02_night_ar.png")

    app.set_lang("en")
    pump(root, 0.6)
    grab_widget(root, "03_night_en.png")

    app.set_theme("day")
    pump(root, 0.6)
    grab_widget(root, "04_day_en.png")

    # ---- About (bilingual explanation + keywords)
    from easyrec.dialogs import AboutDialog, TrimDialog
    about = AboutDialog(root, app)
    about.deiconify()
    pump(root, 0.5)
    grab_widget(about, "05_about.png", pad=2)
    about.destroy()

    # ---- Trim dialog on a real recording, if one exists
    probe_dir = os.path.join(HERE, "reports", "probe_media")
    media = []
    if os.path.isdir(probe_dir):
        media = [os.path.join(probe_dir, f) for f in sorted(os.listdir(probe_dir))
                 if f.endswith(".mp4")]
    if media:
        trim = TrimDialog(root, app, media[0])
        trim.deiconify()
        pump(root, 0.5)
        grab_widget(trim, "06_trim.png", pad=2)
        trim.destroy()

    # ---- floating mini control bar (UI preview, no recording is started)
    from easyrec.minibar import MiniBar
    bar = MiniBar(app)
    bar.set_mode("video")
    bar.update_state("00:12:34", False, "critical", False)
    pump(root, 0.5)
    grab_widget(bar, "07_minibar.png", pad=2)
    bar.destroy()

    # ---- mini bar look (recording state simulated)
    cfg.lang, cfg.theme = "ar", "day"
    cfg.save()
    root.destroy()
    print("done")


if __name__ == "__main__":
    main()
