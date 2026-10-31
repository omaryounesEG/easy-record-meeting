# -*- coding: utf-8 -*-
"""Floating mini control bar shown while the main window is minimized."""

from __future__ import annotations

import tkinter as tk

from .widgets import Chip, RoundButton, TLabel, px, rounded_rect


class MiniBar(tk.Toplevel):
    """Always-on-top bar: timer, state, alarm and transport controls."""

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.colors = app.colors
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=self.colors["bg"])
        self.width, self.height = px(520), px(76)
        self._drag = (0, 0)
        self._alert = "none"
        self._paused = False

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = screen_w - self.width - px(24)
        y = screen_h - self.height - px(90)
        self.geometry(f"{self.width}x{self.height}+{x}+{y}")

        self.canvas = tk.Canvas(self, bg=self.colors["bg"], highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.shell = rounded_rect(self.canvas, 1, 1, self.width - 1, self.height - 1,
                                  px(18), fill=self.colors["surface"],
                                  outline=self.colors["border"], width=2)
        self.canvas.bind("<ButtonPress-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._do_drag)

        self.frame = tk.Frame(self, bg=self.colors["surface"])
        self.frame.place(x=px(10), y=px(10), width=self.width - px(20),
                         height=self.height - px(20))

        side = "right" if app.rtl else "left"
        other = "left" if app.rtl else "right"

        handle = TLabel(self.frame, app, text="⣿", kind="accent", size=11, cursor="fleur")
        handle.pack(side=side, padx=(0, px(4)) if app.rtl else (0, px(4)))
        handle.bind("<ButtonPress-1>", self._start_drag)
        handle.bind("<B1-Motion>", self._do_drag)

        self.mode_chip = Chip(self.frame, app, text="MP4", tone="recording", size=8,
                              pad_x=7, pad_y=3, dot=False)
        self.mode_chip.pack(side=side, padx=px(3))

        self.timer = TLabel(self.frame, app, text="00:00:00", kind="timer", size=15, mono=True)
        self.timer.pack(side=side, padx=px(6))

        self.alert_lbl = TLabel(self.frame, app, text="", kind="danger", size=8.4)
        self.alert_lbl.pack(side=side, padx=px(2))

        self.close_btn = RoundButton(self.frame, app, text="✕", tone="ghost", height=30,
                                     size=8.5, pad_x=8, command=self.app.restore_from_minibar)
        self.close_btn.pack(side=other, padx=(px(2), 0))
        self.expand_btn = RoundButton(self.frame, app, text="⤢", tone="neutral", height=30,
                                      size=9.5, pad_x=9, command=self.app.restore_from_minibar)
        self.expand_btn.pack(side=other, padx=px(2))
        self.stop_btn = RoundButton(self.frame, app, key="minibar.stop", icon="■",
                                    tone="danger", height=30, size=8.6, pad_x=9,
                                    command=self.app.stop_recording)
        self.stop_btn.pack(side=other, padx=px(2))
        self.pause_btn = RoundButton(self.frame, app, key="minibar.pause", icon="❚❚",
                                     tone="warn", height=30, size=8.6, pad_x=9,
                                     command=self.app.toggle_pause)
        self.pause_btn.pack(side=other, padx=px(2))
        self.mute_btn = RoundButton(self.frame, app, text="🔇", tone="danger", height=30,
                                    size=8.6, pad_x=8, command=self.app.mute_alarm)

        self.bind("<Escape>", lambda _e: self.app.restore_from_minibar())

    # ------------------------------------------------------------------ drag
    def _start_drag(self, event):
        self._drag = (event.x_root - self.winfo_x(), event.y_root - self.winfo_y())

    def _do_drag(self, event):
        self.geometry(f"+{event.x_root - self._drag[0]}+{event.y_root - self._drag[1]}")

    # ---------------------------------------------------------------- state
    def set_mode(self, mode: str) -> None:
        self.mode_chip.key = None
        self.mode_chip.literal = "MP3" if mode == "audio" else "MP4"
        self.mode_chip.apply_theme()

    def update_state(self, elapsed_text: str, paused: bool, alert: str = "none",
                     muted: bool = False) -> None:
        self.timer.configure(text=elapsed_text)
        if paused != self._paused:
            self._paused = paused
            if paused:
                self.pause_btn.set_key("minibar.resume")
                self.pause_btn.set_icon("▶")
                self.pause_btn.set_tone("primary")
            else:
                self.pause_btn.set_key("minibar.pause")
                self.pause_btn.set_icon("❚❚")
                self.pause_btn.set_tone("warn")
        if alert != self._alert:
            self._alert = alert
            self._paint_alert(muted)

    def _paint_alert(self, muted: bool = False) -> None:
        colours = self.colors
        critical = self._alert == "critical"
        if critical:
            self.canvas.itemconfigure(self.shell, outline=colours["danger"], width=3)
            self.alert_lbl.set_key("alert.critical.short")
            self.alert_lbl.configure(fg=colours["danger"])
        else:
            self.canvas.itemconfigure(self.shell, outline=colours["border"], width=2)
            self.alert_lbl.set_literal("")
        if critical and not muted and not self.mute_btn.winfo_ismapped():
            self.mute_btn.pack(side="left" if self.app.rtl else "right", padx=px(2))
        if (not critical or muted) and self.mute_btn.winfo_ismapped():
            self.mute_btn.pack_forget()
