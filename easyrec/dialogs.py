# -*- coding: utf-8 -*-
"""Themed modal dialogs: messages, confirmations, trim editor and About.

Native ``tkinter.messagebox`` cannot be themed, so the app speaks through these
rounded, focus-grabbing Toplevels instead.  Each one is bilingual: the caller
passes i18n keys and the text is resolved at open time.
"""

from __future__ import annotations

import os
import threading
import tkinter as tk
import webbrowser
from typing import Callable, Optional, Sequence

from . import engine
from .widgets import Field, RoundButton, TLabel, px, rounded_rect

KIND_TONE = {"info": "primary", "warn": "warn", "error": "danger", "success": "success"}
KIND_GLYPH = {"info": "i", "warn": "!", "error": "✕", "success": "✓"}


class _Modal(tk.Toplevel):
    """Rounded, draggable, grab-taking dialog window."""

    def __init__(self, parent, app, width: float, height: float):
        super().__init__(parent)
        self.app = app
        self.colors = app.colors
        self.withdraw()
        self.overrideredirect(True)
        self.configure(bg=self.colors["bg"])
        self.transient(parent)
        self.attributes("-topmost", True)
        self._width, self._height = px(width), px(height)
        self.result: Optional[str] = None
        self._centre(parent)
        self._drag = (0, 0)
        self.bind("<Escape>", lambda _e: self._cancel())
        self.bind("<ButtonPress-1>", self._start_drag)
        self.bind("<B1-Motion>", self._do_drag)
        try:
            if getattr(app, "icon_photo", None):
                self.iconphoto(True, app.icon_photo)
        except Exception:
            pass

        self.canvas = tk.Canvas(self, bg=self.colors["bg"], highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self._paint_shell()
        self.frame = tk.Frame(self, bg=self.colors["surface"])
        self.frame.place(x=px(1), y=px(1), width=self._width - px(2),
                         height=self._height - px(2))

    def _paint_shell(self) -> None:
        self.canvas.delete("shell")
        rounded_rect(self.canvas, 1, 1, self._width - 1, self._height - 1, px(18),
                     fill=self.colors["surface"], outline=self.colors["border"], width=1)

    def _centre(self, parent) -> None:
        try:
            parent.update_idletasks()
            root_x, root_y = parent.winfo_rootx(), parent.winfo_rooty()
            pw, ph = parent.winfo_width(), parent.winfo_height()
        except Exception:
            root_x = root_y = 100
            pw, ph = 1200, 800
        x = root_x + max(0, (pw - self._width) // 2)
        y = root_y + max(0, (ph - self._height) // 3)
        self.geometry(f"{self._width}x{self._height}+{x}+{y}")

    def _start_drag(self, event):
        self._drag = (event.x_root - self.winfo_x(), event.y_root - self.winfo_y())

    def _do_drag(self, event):
        self.geometry(f"+{event.x_root - self._drag[0]}+{event.y_root - self._drag[1]}")

    def _cancel(self):
        self.result = None
        self.destroy()

    def show(self):
        self.deiconify()
        self.lift()
        self.grab_set()
        self.focus_force()
        self.wait_window()
        return self.result


class MessageDialog(_Modal):
    def __init__(self, parent, app, title_key: str, body: str, kind: str = "info",
                 buttons: Sequence[tuple] = (("btn.ok", "primary", "ok"),),
                 body_is_key: bool = False, body_kwargs: Optional[dict] = None,
                 width: float = 430):
        body_text = app.t(body, **(body_kwargs or {})) if body_is_key else body
        lines = max(2, body_text.count("\n") + 1 + len(body_text) // 48)
        height = 150 + min(lines, 9) * 18      # _Modal applies the DPI scale
        super().__init__(parent, app, width=width, height=height)

        pad = px(20)
        header = tk.Frame(self.frame, bg=self.colors["surface"])
        header.pack(fill="x", padx=pad, pady=(px(18), px(8)))

        tone = KIND_TONE.get(kind, "primary")
        badge = tk.Canvas(header, width=px(28), height=px(28), bg=self.colors["surface"],
                          highlightthickness=0, bd=0)
        badge.pack(side="right" if app.rtl else "left", padx=(0, px(10)) if app.rtl else (0, px(10)))
        rounded_rect(badge, 1, 1, px(28) - 1, px(28) - 1, px(9), fill=app.colors[tone])
        badge.create_text(px(14), px(14), text=KIND_GLYPH.get(kind, "i"),
                          fill=app.colors.get("on_" + tone, "#FFFFFF"),
                          font=(app.fonts["body"], px(12), "bold"))

        TLabel(header, app, key=title_key, kind="strong", size=12,
               anchor="e" if app.rtl else "w").pack(
            side="right" if app.rtl else "left", fill="x", expand=True)

        TLabel(self.frame, app, text=body_text, kind="muted", size=9.8,
               justify="right" if app.rtl else "left", wraplength=self._width - pad * 2,
               anchor="e" if app.rtl else "w").pack(fill="x", padx=pad)

        spacer = tk.Frame(self.frame, bg=self.colors["surface"], height=px(14))
        spacer.pack(fill="x")

        actions = tk.Frame(self.frame, bg=self.colors["surface"])
        actions.pack(fill="x", padx=pad, pady=(0, px(16)), side="bottom")
        for key, tone_name, value in buttons:
            btn = RoundButton(actions, app, key=key, tone=tone_name or "neutral",
                              height=38, size=10, pad_x=18,
                              command=lambda v=value: self._choose(v))
            btn.pack(side="right" if app.rtl else "left", padx=(0, px(8)))
        self.bind("<Return>", lambda _e: self._choose(buttons[-1][2] if buttons else "ok"))

    def _choose(self, value):
        self.result = value
        self.destroy()


def info(parent, app, title_key: str, body: str, kind: str = "info",
         body_is_key: bool = False, body_kwargs: Optional[dict] = None) -> None:
    MessageDialog(parent, app, title_key, body, kind=kind,
                  body_is_key=body_is_key, body_kwargs=body_kwargs).show()


def error(parent, app, title_key: str, body: str) -> None:
    info(parent, app, title_key, body, kind="error")


def confirm(parent, app, title_key: str, body: str, body_is_key: bool = False,
            body_kwargs: Optional[dict] = None) -> bool:
    dlg = MessageDialog(parent, app, title_key, body, kind="warn", body_is_key=body_is_key,
                        body_kwargs=body_kwargs,
                        buttons=(("btn.cancel", "neutral", "cancel"), ("btn.ok", "primary", "ok")))
    return dlg.show() == "ok"


# --------------------------------------------------------------------- trim
class TrimDialog(_Modal):
    def __init__(self, parent, app, file_path: str, on_saved: Optional[Callable[[str], None]] = None):
        super().__init__(parent, app, width=520, height=372)
        self.file_path = file_path
        self.on_saved = on_saved
        self.total = engine.media_duration(app.ffmpeg, file_path)
        self._busy = False
        self._build()
        self._title_key = "trim.title"

    def _build(self) -> None:
        app, colours = self.app, self.colors
        pad = px(20)

        head = tk.Frame(self.frame, bg=colours["surface"])
        head.pack(fill="x", padx=pad, pady=(px(16), px(6)))
        TLabel(head, app, key="trim.title", kind="strong", size=12.5).pack(
            side="right" if app.rtl else "left")
        close = RoundButton(head, app, text="✕", tone="ghost", height=28, size=9,
                            pad_x=8, command=self._cancel)
        close.pack(side="left" if app.rtl else "right")

        info_row = tk.Frame(self.frame, bg=colours["surface"])
        info_row.pack(fill="x", padx=pad, pady=(0, px(6)))
        TLabel(info_row, app, text=os.path.basename(self.file_path), kind="muted",
               size=9).pack(side="right" if app.rtl else "left", fill="x", expand=True)
        TLabel(info_row, app, text=f"{app.t('trim.duration')}: {engine.format_duration(self.total)}",
               kind="success", size=9).pack(side="left" if app.rtl else "right")

        clip = tk.Frame(self.frame, bg=colours["surface"])
        clip.pack(fill="x", padx=pad, pady=(0, px(10)))
        RoundButton(clip, app, key="trim.play", icon="▶", tone="soft", height=34, size=9.5,
                    command=self._play).pack(side="right" if app.rtl else "left")

        times = tk.Frame(self.frame, bg=colours["surface"])
        times.pack(fill="x", padx=pad)
        self.start_entry = self._time_field(times, "trim.start", "00:00:00")
        self.end_entry = self._time_field(times, "trim.end",
                                          engine.format_duration(self.total))

        TLabel(self.frame, app, key="trim.hint", kind="faint", size=8.5,
               wraplength=self._width - pad * 2,
               justify="right" if app.rtl else "left").pack(
            fill="x", padx=pad, pady=(px(8), px(2)))

        self.status = TLabel(self.frame, app, text="", kind="muted", size=9)
        self.status.pack(fill="x", padx=pad, pady=(px(4), 0))

        actions = tk.Frame(self.frame, bg=colours["surface"])
        actions.pack(fill="x", padx=pad, pady=(0, px(16)), side="bottom")
        self.cut_btn = RoundButton(actions, app, key="trim.cut", icon="✂", tone="primary",
                                   height=40, size=10, command=self._cut)
        self.cut_btn.pack(side="right" if app.rtl else "left", fill="x", expand=True,
                          padx=(px(6), 0) if app.rtl else (0, px(6)))
        self.keep_btn = RoundButton(actions, app, key="trim.keep", tone="neutral", height=40,
                                    size=10, command=self._keep)
        self.keep_btn.pack(side="right" if app.rtl else "left", fill="x", expand=True,
                           padx=(0, px(6)) if app.rtl else (px(6), 0))

    def _time_field(self, parent, key: str, value: str) -> Field:
        row = tk.Frame(parent, bg=self.colors["surface"])
        row.pack(fill="x", pady=px(3))
        TLabel(row, app=self.app, key=key, kind="muted", size=9.5).pack(
            side="right" if self.app.rtl else "left", padx=(0, px(10)) if self.app.rtl else (0, px(10)))
        field = Field(row, self.app, height=38)
        field.pack(side="right" if self.app.rtl else "left", fill="x", expand=True)
        field.entry.insert(0, value)
        field.entry.configure(font=(self.app.fonts["mono"], px(11), "bold"), justify="center")
        return field

    # ---------------------------------------------------------------- actions
    def _play(self):
        try:
            os.startfile(self.file_path)
        except Exception as exc:
            info(self, self.app, "dlg.error", str(exc), kind="error")

    def _keep(self):
        self.result = self.file_path
        if self.on_saved:
            self.on_saved(self.file_path)
        self.destroy()

    def _cut(self):
        if self._busy:
            return
        try:
            start = engine.parse_timestamp(self.start_entry.get())
            end = engine.parse_timestamp(self.end_entry.get())
        except ValueError:
            self._fail(self.app.t("trim.invalid"))
            return
        if end <= start:
            self._fail(self.app.t("trim.invalid"))
            return
        if self.total and start >= self.total - 0.05:
            self._fail(self.app.t("trim.invalid"))
            return

        base, ext = os.path.splitext(self.file_path)
        destination = f"{base}_{engine.format_duration(start).replace(':', '-')}_{ext}"
        self._busy = True
        self.cut_btn.set_enabled(False)
        self.keep_btn.set_enabled(False)
        self.status.set_key("trim.working")
        self.status.configure(fg=self.colors["primary"])

        def worker():
            try:
                proc = engine.cut_segment(self.app.ffmpeg, self.file_path, start,
                                          min(end, self.total) if self.total else end,
                                          destination)
                ok = proc.returncode == 0 and os.path.exists(destination) \
                    and os.path.getsize(destination) > 0
            except Exception as exc:
                ok, destination = False, str(exc)
            self.after(0, lambda: self._done(ok, destination))

        threading.Thread(target=worker, daemon=True).start()

    def _done(self, ok: bool, destination: str):
        self._busy = False
        self.cut_btn.set_enabled(True)
        self.keep_btn.set_enabled(True)
        if not ok:
            self._fail(self.app.t("trim.failed"))
            return
        self.result = destination
        if self.on_saved:
            self.on_saved(destination)
        info(self, self.app, "dlg.info",
             self.app.t("trim.success", name=os.path.basename(destination)), kind="success")
        self.destroy()

    def _fail(self, message: str):
        self.status.set_literal(message)
        self.status.configure(fg=self.colors["danger"])


# -------------------------------------------------------------------- about
class AboutDialog(_Modal):
    def __init__(self, parent, app):
        super().__init__(parent, app, width=560, height=486)
        colours = self.colors
        pad = px(22)
        from . import APP_VERSION, GITHUB_URL, PUBLISHER, VERSION_TAG

        head = tk.Frame(self.frame, bg=colours["surface"])
        head.pack(fill="x", padx=pad, pady=(px(18), px(8)))

        if getattr(app, "icon_photo_large", None):
            logo = tk.Label(head, image=app.icon_photo_large, bg=colours["surface"], bd=0)
            logo.pack(side="right" if app.rtl else "left", padx=(0, px(12)) if app.rtl else (0, px(12)))

        titles = tk.Frame(head, bg=colours["surface"])
        titles.pack(side="right" if app.rtl else "left", fill="x", expand=True)
        TLabel(titles, app, text="Easy Record Meeting", kind="strong", size=14,
               anchor="e" if app.rtl else "w").pack(fill="x")
        TLabel(titles, app, key="app.title", kind="muted", size=10,
               anchor="e" if app.rtl else "w").pack(fill="x")
        TLabel(titles, app, text=f"{VERSION_TAG} • {PUBLISHER}", kind="faint", size=8.5,
               anchor="e" if app.rtl else "w").pack(fill="x")

        text = tk.Frame(self.frame, bg=colours["surface"])
        text.pack(fill="both", expand=True, padx=pad)

        TLabel(text, app, key="about.desc.ar", kind="body", size=9.3,
               wraplength=self._width - pad * 2.4,
               justify="right" if app.rtl else "left").pack(fill="x", pady=(0, px(6)))
        TLabel(text, app, key="about.desc.en", kind="muted", size=9.3,
               wraplength=self._width - pad * 2.4,
               justify="right" if app.rtl else "left").pack(fill="x", pady=(0, px(6)))
        TLabel(text, app, key="about.keywords.ar", kind="faint", size=8.2,
               wraplength=self._width - pad * 2.4,
               justify="right" if app.rtl else "left").pack(fill="x", pady=(0, px(2)))
        TLabel(text, app, key="about.keywords.en", kind="faint", size=8.2,
               wraplength=self._width - pad * 2.4,
               justify="right" if app.rtl else "left").pack(fill="x", pady=(0, px(6)))
        TLabel(text, app, key="about.shortcut", kind="faint", size=8.2,
               wraplength=self._width - pad * 2.4,
               justify="right" if app.rtl else "left").pack(fill="x")

        actions = tk.Frame(self.frame, bg=colours["surface"])
        actions.pack(fill="x", padx=pad, pady=(px(8), px(16)), side="bottom")
        RoundButton(actions, app, text="GitHub", icon="↗", tone="soft", height=36, size=9.5,
                    command=lambda: webbrowser.open(GITHUB_URL)).pack(
            side="right" if app.rtl else "left")
        RoundButton(actions, app, key="btn.close", tone="primary", height=36, size=9.5,
                    command=self.destroy).pack(side="left" if app.rtl else "right")
