# -*- coding: utf-8 -*-
"""Main window: light-first bilingual UI with day/night modes.

Everything is built from the rounded primitives in :mod:`easyrec.widgets`, so a
theme or language change is applied in-place (``apply_theme`` / ``retranslate``)
and never interrupts an active recording.  Only a direction change (AR <-> EN)
rebuilds the layout, because Tk has no native RTL mirroring.
"""

from __future__ import annotations

import os
import queue
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import filedialog, ttk
from typing import Callable, Dict, List, Optional

from . import (APP_NAME_FULL, APP_VERSION, GITHUB_REPO, GITHUB_URL, RELEASES_URL,
               VERSION_TAG, dialogs, engine, fonts, i18n, updater)
from .config import Config, asset_path, default_output_dir
from .minibar import MiniBar
from .theme import palette
from .widgets import (Card, Chip, ChoiceTile, Field, Meter, RoundButton, Segmented,
                      TCombo, TFrame, TLabel, ToggleSwitch, px, set_scale)

STATUS_STYLE = {
    "idle": ("status.idle", "idle"),
    "paused": ("status.paused", "paused"),
    "finishing": ("status.finishing", "busy"),
    "done": ("status.saved", "success"),
    "error": ("status.error", "danger"),
}

ACTIVE_STATES = ("recording", "paused", "finishing")


class ScrollArea(tk.Frame):
    """Vertically scrollable body; the scrollbar appears only when needed."""

    def __init__(self, master, app):
        super().__init__(master, bg=app.colors["bg"])
        self.app = app
        self.canvas = tk.Canvas(self, bg=app.colors["bg"], highlightthickness=0, bd=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview,
                                 style="Easy.Vertical.TScrollbar")
        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.inner = tk.Frame(self.canvas, bg=app.colors["bg"])
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._sync)
        self.canvas.bind("<Configure>", self._on_canvas)
        self.canvas.bind("<Enter>", lambda _e: self._bind_wheel())
        self.canvas.bind("<Leave>", lambda _e: self._unbind_wheel())
        self.inner.bind("<Enter>", lambda _e: self._bind_wheel())

    def _on_scroll(self, first, last):
        self.bar.set(first, last)
        needed = not (float(first) <= 0.0 and float(last) >= 1.0)
        if needed and not self.bar.winfo_ismapped():
            self.bar.pack(side="right", fill="y")
        elif not needed and self.bar.winfo_ismapped():
            self.bar.pack_forget()

    def _sync(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas(self, event):
        self.canvas.itemconfigure(self._window, width=event.width)

    def _bind_wheel(self):
        self.canvas.bind_all("<MouseWheel>", self._wheel)

    def _unbind_wheel(self):
        self.canvas.unbind_all("<MouseWheel>")

    def _wheel(self, event):
        try:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    def apply_theme(self):
        if not self.winfo_exists():
            return
        colours = self.app.colors
        self.configure(bg=colours["bg"])
        self.canvas.configure(bg=colours["bg"])
        self.inner.configure(bg=colours["bg"])
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Easy.Vertical.TScrollbar", background=colours["surface_alt"],
                        troughcolor=colours["bg"], bordercolor=colours["bg"],
                        arrowcolor=colours["text_muted"], width=px(10))


class EasyRecordApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.widgets: List[object] = []
        self.cfg = Config.load()
        self._lang = self.cfg.lang if self.cfg.lang in i18n.LANGS else "ar"
        self._theme_name = self.cfg.theme if self.cfg.theme in ("day", "night") else "day"
        self.ffmpeg = engine.resolve_ffmpeg()
        self.recorder = engine.Recorder(ffmpeg=self.ffmpeg)

        self.fonts = fonts.resolve(root, logger=self.log)
        try:
            set_scale(root.winfo_fpixels("1i") / 96.0)
        except Exception:
            set_scale(1.0)

        self.queue: "queue.Queue[Callable]" = queue.Queue()
        self.devices: Dict[str, object] = {}
        self.minibar: Optional[MiniBar] = None
        self._stop_requested = False
        self._stop_thread: Optional[threading.Thread] = None
        self._last_beep = 0.0
        self._flash = False
        self._prev_alert = "none"
        self._recovered_until = 0.0
        self._closing = False
        self._error_reported = False
        self._after_id: Optional[str] = None
        self._timer_text = ""
        self._border_state: tuple = ()

        self.icon_photo = None
        self.icon_photo_large = None
        self._load_icons()

        self.mode_var = tk.StringVar(value=self.cfg.mode if self.cfg.mode in ("video", "audio") else "video")
        self.dir_var = tk.StringVar(value=self.cfg.directory or default_output_dir())
        self.device_var = tk.StringVar(value=i18n.tr(self._lang, "device.loading"))
        self.url_var = tk.StringVar()
        self.auto_open_var = tk.BooleanVar(value=self.cfg.auto_open)
        self.auto_mini_var = tk.BooleanVar(value=self.cfg.auto_mini)

        self._build_layout()
        self._refresh_devices()
        self._bind_shortcuts()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Destroy>", self._on_destroy_root, add="+")
        self._after_id = self.root.after(250, self._poll)

    # ------------------------------------------------------------------ basics
    def log(self, message: str) -> None:
        try:
            print(message, flush=True)
        except Exception:
            pass

    def post(self, fn: Callable) -> None:
        """Run ``fn`` on the Tk thread from any worker thread."""
        self.queue.put(fn)

    @property
    def lang(self) -> str:
        return self._lang

    @property
    def rtl(self) -> bool:
        return i18n.is_rtl(self._lang)

    @property
    def theme_name(self) -> str:
        return self._theme_name

    @property
    def colors(self) -> Dict[str, str]:
        return palette(self._theme_name)

    def t(self, key: str, **kwargs) -> str:
        return i18n.tr(self._lang, key, **kwargs)

    @property
    def side(self) -> str:
        return "right" if self.rtl else "left"

    @property
    def other(self) -> str:
        return "left" if self.rtl else "right"

    # ------------------------------------------------------------------ icons
    def _load_icons(self) -> None:
        ico = asset_path("icon.ico")
        if os.path.exists(ico):
            try:
                self.root.iconbitmap(ico)
            except Exception as exc:
                self.log(f"[icon] iconbitmap failed: {exc}")
        png = asset_path("icon.png")
        if not os.path.exists(png):
            return
        try:
            from PIL import Image, ImageDraw, ImageTk

            image = Image.open(png).convert("RGBA")

            def rounded(size: int):
                small = image.resize((size, size), Image.LANCZOS)
                mask = Image.new("L", (size, size), 0)
                ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1],
                                                       radius=int(size * 0.22), fill=255)
                small.putalpha(mask)
                return ImageTk.PhotoImage(small)

            self.icon_photo = rounded(px(38))
            self.icon_photo_large = rounded(px(64))
        except Exception as exc:
            self.log(f"[icon] png load failed: {exc}")

    # ----------------------------------------------------------------- layout
    def _build_layout(self) -> None:
        colours = self.colors
        self.root.configure(bg=colours["bg"])
        self.root.title(f"{APP_NAME_FULL} — {self.t('app.title')}")
        try:
            screen_w, screen_h = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            width = min(px(900), int(screen_w * 0.94))
            height = min(px(960), int(screen_h * 0.90))
            x = max(0, (screen_w - width) // 2)
            y = max(0, (screen_h - height) // 2 - px(24))
            self.root.geometry(f"{width}x{height}+{x}+{y}")
            self.root.minsize(min(px(760), width), min(px(620), height))
        except Exception:
            pass

        self._build_topbar()
        self.footer = TFrame(self.root, self, role="bg")
        self.footer.pack(side="bottom", fill="x", padx=px(18), pady=(0, px(10)))
        self._build_footer()

        self.scroll = ScrollArea(self.root, self)
        self.scroll.pack(fill="both", expand=True)
        body = TFrame(self.scroll.inner, self, role="bg", padx=px(18), pady=px(12))
        body.pack(fill="both", expand=True)
        self.body = body

        self._build_setup_card(body)
        self._build_session_card(body)
        self._build_monitor_card(body)
        self._build_controls(body)
        self._render(self.recorder.snapshot())
        self.root.update_idletasks()
        self.scroll._sync()

    def _build_topbar(self) -> None:
        colours = self.colors
        bar = TFrame(self.root, self, role="surface")
        bar.pack(side="top", fill="x")
        TFrame(self.root, self, role="border", height=1).pack(side="top", fill="x")
        self.topbar = bar

        inner = TFrame(bar, self, role="surface", padx=px(18), pady=px(10))
        inner.pack(fill="x")

        brand = TFrame(inner, self, role="surface")
        brand.pack(side=self.side, fill="x", expand=True)
        if self.icon_photo:
            logo = tk.Label(brand, image=self.icon_photo, bg=colours["surface"], bd=0)
            logo.pack(side=self.side, padx=(0, px(10)) if self.rtl else (0, px(10)))
        titles = TFrame(brand, self, role="surface")
        titles.pack(side=self.side)
        TLabel(titles, app=self, text=APP_NAME_FULL, kind="strong", size=13.5,
               anchor="e" if self.rtl else "w").pack(anchor="e" if self.rtl else "w")
        TLabel(titles, app=self, key="app.tagline", kind="faint", size=8.8,
               anchor="e" if self.rtl else "w").pack(anchor="e" if self.rtl else "w")
        self.version_chip = Chip(inner, app=self, text=VERSION_TAG, tone="muted",
                                 size=8.4, pad_x=9, pad_y=4, dot=False)
        self.version_chip.pack(side=self.side, padx=px(8))

        controls = TFrame(inner, self, role="surface")
        controls.pack(side=self.other)

        self.about_btn = RoundButton(controls, app=self, text="", icon="ⓘ", tone="ghost",
                                     height=34, width=40, pad_x=8, command=self.show_about)
        self.about_btn.pack(side=self.other, padx=px(4))
        self.update_btn = RoundButton(controls, app=self, key="btn.update", icon="↻",
                                      tone="soft", height=34, size=9.5, pad_x=12,
                                      command=self.check_updates)
        self.update_btn.pack(side=self.other, padx=px(4))
        self.theme_seg = Segmented(controls, app=self,
                                   options=[("day", "theme.day"), ("night", "theme.night")],
                                   value=self._theme_name, command=self.set_theme,
                                   size=9, height=32)
        self.theme_seg.pack(side=self.other, padx=px(4))
        self.lang_seg = Segmented(controls, app=self,
                                  options=[("ar", "العربية"), ("en", "English")],
                                  value=self._lang, command=self.set_lang, size=9, height=32)
        self.lang_seg.pack(side=self.other, padx=px(4))

    def _build_footer(self) -> None:
        colours = self.colors
        self.footer_status = TLabel(self.footer, app=self, text="", kind="faint", size=8.4)
        self.footer_status.pack(side=self.side)
        TLabel(self.footer, app=self, key="footer.hint", kind="faint", size=8.4).pack(
            side=self.other)
        TLabel(self.footer, app=self, text=f"{self.t('footer.made')} • {VERSION_TAG}",
               kind="faint", size=8.4).pack(side=self.other, padx=px(10))

    # ------------------------------------------------------------ setup card
    def _build_setup_card(self, parent) -> None:
        colours = self.colors
        card = Card(parent, self, "card.setup", "card.setup.hint")
        card.pack(fill="x", pady=(0, px(10)))
        self.card_setup = card
        body = card.body

        tiles = TFrame(body, self, role="surface")
        tiles.pack(fill="x", pady=(0, px(10)))
        tiles.columnconfigure(0, weight=1, uniform="tile")
        tiles.columnconfigure(1, weight=1, uniform="tile")
        self.tile_video = ChoiceTile(tiles, self, "video", "mode.video", "mode.video.desc",
                                     self.mode_var, command=self._on_mode_change)
        self.tile_audio = ChoiceTile(tiles, self, "audio", "mode.audio", "mode.audio.desc",
                                     self.mode_var, command=self._on_mode_change)
        left_index, right_index = (1, 0) if self.rtl else (0, 1)
        self.tile_video.grid(row=0, column=left_index, sticky="ew",
                             padx=(0, px(6)) if self.rtl else (0, px(6)))
        self.tile_audio.grid(row=0, column=right_index, sticky="ew",
                             padx=(px(6), 0) if self.rtl else (px(6), 0))

        head = TFrame(body, self, role="surface")
        head.pack(fill="x", pady=(0, px(2)))
        TLabel(head, app=self, key="device.label", kind="section", size=9.2).pack(side=self.side)
        TLabel(head, app=self, key="device.hint", kind="faint", size=8.2).pack(
            side=self.side, padx=px(8))

        row = TFrame(body, self, role="surface")
        row.pack(fill="x", pady=(0, px(8)))
        self.test_btn = RoundButton(row, app=self, key="btn.test_signal", icon="◎",
                                    tone="neutral", height=38, size=9, pad_x=12,
                                    command=self.test_signal)
        self.test_btn.pack(side=self.other, padx=(px(6), 0) if self.rtl else (px(6), 0))
        self.refresh_btn = RoundButton(row, app=self, text="⟳", tone="ghost", height=38,
                                       width=40, pad_x=8, command=self._refresh_devices)
        self.refresh_btn.pack(side=self.other, padx=(px(6), 0) if self.rtl else (px(6), 0))
        self.device_combo = TCombo(row, self, textvariable=self.device_var)
        self.device_combo.pack(side=self.side, fill="x", expand=True)

        tools = TFrame(body, self, role="surface")
        tools.pack(fill="x")
        self.vdesk_btn = RoundButton(tools, app=self, key="tools.vdesk", icon="▣",
                                     tone="soft", height=36, size=9, pad_x=10,
                                     command=self.open_virtual_desktop)
        self.vdesk_btn._stretched = True
        self.vdesk_btn.pack(side=self.side, fill="x", expand=True,
                            padx=(0, px(5)) if self.rtl else (0, px(5)))
        self.trim_btn = RoundButton(tools, app=self, key="tools.trim", icon="✂",
                                    tone="soft", height=36, size=9, pad_x=10,
                                    command=self.open_trim_dialog)
        self.trim_btn._stretched = True
        self.trim_btn.pack(side=self.side, fill="x", expand=True,
                           padx=(px(5), 0) if self.rtl else (px(5), 0))

    # ---------------------------------------------------------- session card
    def _build_session_card(self, parent) -> None:
        colours = self.colors
        card = Card(parent, self, "card.session")
        card.pack(fill="x", pady=(0, px(10)))
        self.card_session = card
        body = card.body

        TLabel(body, app=self, key="link.label", kind="section", size=9.2).pack(
            fill="x", anchor="e" if self.rtl else "w", pady=(0, px(3)))
        link_row = TFrame(body, self, role="surface")
        link_row.pack(fill="x", pady=(0, px(8)))
        self.paste_btn = RoundButton(link_row, app=self, key="btn.paste", icon="⌘",
                                     tone="ghost", height=38, size=9, pad_x=10,
                                     command=self.paste_link)
        self.paste_btn.pack(side=self.other, padx=(px(6), 0) if self.rtl else (px(6), 0))
        self.link_field = Field(link_row, self, textvariable=self.url_var)
        self.link_field.pack(side=self.side, fill="x", expand=True)

        toggles = TFrame(body, self, role="surface")
        toggles.pack(fill="x", pady=(0, px(8)))
        for index, (variable, key) in enumerate(((self.auto_open_var, "opt.auto_open"),
                                                 (self.auto_mini_var, "opt.auto_mini"))):
            pair = TFrame(toggles, self, role="surface")
            pair.pack(side=self.side, padx=(0, px(16)) if self.rtl else (0, px(16)))
            ToggleSwitch(pair, self, variable, command=self._save_toggles).pack(side=self.side)
            TLabel(pair, app=self, key=key, kind="muted", size=9).pack(
                side=self.side, padx=px(8))

        TLabel(body, app=self, key="dir.label", kind="section", size=9.2).pack(
            fill="x", anchor="e" if self.rtl else "w", pady=(0, px(3)))
        dir_row = TFrame(body, self, role="surface")
        dir_row.pack(fill="x")
        self.browse_btn = RoundButton(dir_row, app=self, key="btn.browse", icon="📂",
                                      tone="ghost", height=38, size=9, pad_x=10,
                                      command=self.browse_directory)
        self.browse_btn.pack(side=self.other, padx=(px(6), 0) if self.rtl else (px(6), 0))
        self.open_btn = RoundButton(dir_row, app=self, key="btn.open_folder", icon="↗",
                                    tone="ghost", height=38, size=9, pad_x=10,
                                    command=self.open_folder)
        self.open_btn.pack(side=self.other, padx=(px(6), 0) if self.rtl else (px(6), 0))
        self.dir_field = Field(dir_row, self, textvariable=self.dir_var)
        self.dir_field.pack(side=self.side, fill="x", expand=True)
        self.dir_var.trace_add("write", lambda *_: self._save_dir())

    # ---------------------------------------------------------- monitor card
    def _build_monitor_card(self, parent) -> None:
        colours = self.colors
        card = Card(parent, self, "card.monitor")
        card.pack(fill="x", pady=(0, px(10)))
        self.monitor_card = card
        body = card.body

        top = TFrame(body, self, role="surface")
        top.pack(fill="x")
        self.status_chip = Chip(top, app=self, key="status.idle", tone="idle", size=9, pad_x=11)
        self.status_chip.pack(side=self.side)
        self.info_lbl = TLabel(top, app=self, text="", kind="faint", size=8.6)
        self.info_lbl.pack(side=self.other)

        self.timer_lbl = TLabel(body, app=self, text="00:00:00", kind="timer", size=32, mono=True)
        self.timer_lbl.pack(pady=(px(6), px(2)))

        meter_row = TFrame(body, self, role="surface")
        meter_row.pack(fill="x", pady=(px(4), 0))
        self.meter_lbl = TLabel(meter_row, app=self, key="monitor.meter", kind="faint", size=8.4)
        self.meter_lbl.pack(side=self.side, padx=(0, px(8)) if self.rtl else (0, px(8)))
        self.meter = Meter(meter_row, self, height=14)
        self.meter.pack(side=self.side, fill="x", expand=True)

        alert_row = TFrame(body, self, role="surface")
        alert_row.pack(fill="x", pady=(px(8), 0))
        self.alert_lbl = TLabel(alert_row, app=self, text="", kind="danger", size=9,
                                wraplength=px(520),
                                justify="right" if self.rtl else "left")
        self.alert_lbl.pack(side=self.side, fill="x", expand=True)
        self.mute_btn = RoundButton(alert_row, app=self, key="btn.mute_alarm", icon="🔇",
                                    tone="danger", height=32, size=8.6, pad_x=10,
                                    command=self.mute_alarm)
        self.hint_lbl = TLabel(body, app=self, key="monitor.idle_hint", kind="faint", size=8.6)
        self.hint_lbl.pack(pady=(px(4), 0))

    # -------------------------------------------------------------- controls
    def _build_controls(self, parent) -> None:
        colours = self.colors
        row = TFrame(parent, self, role="bg")
        row.pack(fill="x", pady=(px(2), px(4)))
        self.start_btn = RoundButton(row, app=self, key="btn.start.video", icon="●",
                                     tone="primary", height=52, size=11.5, pad_x=14,
                                     command=self.start_recording)
        self.start_btn._stretched = True
        self.start_btn.pack(side=self.side, fill="x", expand=True)
        self.pause_btn = RoundButton(row, app=self, key="btn.pause", icon="❚❚",
                                     tone="neutral", height=52, size=10.5, pad_x=12,
                                     width=132, command=self.toggle_pause)
        self.pause_btn.pack(side=self.side, fill="x", padx=px(6))
        self.stop_btn = RoundButton(row, app=self, key="btn.stop", icon="■", tone="danger",
                                    height=52, size=10.5, pad_x=12, width=148,
                                    command=self.stop_recording)
        self.stop_btn.pack(side=self.side, fill="x")

    # ------------------------------------------------------------- shortcuts
    def _bind_shortcuts(self) -> None:
        bindings = {
            "<Control-r>": lambda e: self._toggle_record(),
            "<Control-R>": lambda e: self._toggle_record(),
            "<Control-p>": lambda e: self.toggle_pause(),
            "<Control-P>": lambda e: self.toggle_pause(),
            "<Control-l>": lambda e: self.set_lang("en" if self._lang == "ar" else "ar"),
            "<Control-t>": lambda e: self.set_theme("night" if self._theme_name == "day" else "day"),
            "<Control-u>": lambda e: self.check_updates(),
            "<F1>": lambda e: self.show_about(),
        }
        for sequence, handler in bindings.items():
            try:
                self.root.bind(sequence, handler)
            except Exception:
                pass

    def _toggle_record(self):
        if self.recorder.status in ACTIVE_STATES:
            self.stop_recording()
        else:
            self.start_recording()

    # ---------------------------------------------------------------- config
    def _save_toggles(self) -> None:
        self.cfg.auto_open = bool(self.auto_open_var.get())
        self.cfg.auto_mini = bool(self.auto_mini_var.get())
        self.cfg.save()

    def _save_dir(self) -> None:
        self.cfg.directory = self.dir_var.get().strip()
        self.cfg.save()

    def _persist(self) -> None:
        self.cfg.mode = self.mode_var.get()
        self.cfg.directory = self.dir_var.get().strip()
        self.cfg.lang = self._lang
        self.cfg.theme = self._theme_name
        self.cfg.auto_open = bool(self.auto_open_var.get())
        self.cfg.auto_mini = bool(self.auto_mini_var.get())
        self.cfg.save()

    def _on_mode_change(self, value: str | None = None) -> None:
        self.cfg.mode = self.mode_var.get()
        self.cfg.save()
        if hasattr(self, "tile_video"):
            self.tile_video.apply_theme()
            self.tile_audio.apply_theme()
        self._sync_start_button()

    # ------------------------------------------------------------- theme/lang
    def set_theme(self, name: str) -> None:
        if name not in ("day", "night") or name == self._theme_name:
            return
        self._theme_name = name
        self.cfg.theme = name
        self.cfg.save()
        for widget in list(self.widgets):
            try:
                widget.apply_theme()
            except Exception as exc:
                self.log(f"[theme] {type(widget).__name__}: {exc}")
        self.root.configure(bg=self.colors["bg"])
        try:
            self.scroll.apply_theme()
            self.theme_seg.set_value(name, notify=False)
        except Exception:
            pass
        for frame, role in ((getattr(self, "topbar", None), "surface"),
                            (getattr(self, "footer", None), "bg")):
            if frame is not None:
                try:
                    frame.configure(bg=self.colors[role])
                except Exception:
                    pass

    def set_lang(self, lang: str) -> None:
        if lang not in i18n.LANGS or lang == self._lang:
            return
        direction_changed = i18n.is_rtl(lang) != i18n.is_rtl(self._lang)
        self._lang = lang
        self.cfg.lang = lang
        self.cfg.save()
        if direction_changed:
            self._rebuild_layout()
        else:
            for widget in list(self.widgets):
                try:
                    widget.retranslate()
                except Exception as exc:
                    self.log(f"[lang] {type(widget).__name__}: {exc}")
            try:
                self.lang_seg.set_value(lang, notify=False)
            except Exception:
                pass

    def _rebuild_layout(self) -> None:
        """Rebuild the whole tree so AR/EN mirroring is real, not cosmetic."""
        for child in list(self.root.winfo_children()):
            if isinstance(child, tk.Toplevel):
                continue
            child.destroy()
        self.widgets = [w for w in self.widgets if _alive(w)]
        self._build_layout()
        self._refresh_devices()
        self._render(self.recorder.snapshot())

    # --------------------------------------------------------------- devices
    def _refresh_devices(self, notify: bool = False) -> None:
        try:
            if not self.devices:
                self.device_combo.set_values([self.t("device.loading")])
        except Exception:
            pass

        def worker():
            try:
                devices = engine.list_devices()
                error = None
            except Exception as exc:
                devices, error = [], str(exc)
            self.post(lambda: self._apply_devices(devices, error, notify))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_devices(self, devices, error, notify: bool) -> None:
        self.devices = {}
        names: List[str] = []
        for index, device in enumerate(devices):
            suffix = f" ({self.t('device.default')})" if index == 0 else ""
            display = f"🔊 {getattr(device, 'name', 'device')}{suffix}"
            self.devices[display] = device
            names.append(display)
        try:
            self.device_combo.set_values(names or [self.t("device.none")])
            current = self.device_var.get()
            if current not in names:
                self.device_var.set(names[0] if names else self.t("device.none"))
        except Exception as exc:
            self.log(f"[devices] {exc}")
        if error:
            self.log(f"[devices] error: {error}")
            if notify:
                dialogs.error(self.root, self, "dlg.error", error)

    def _selected_device(self):
        return self.devices.get(self.device_var.get())

    # ---------------------------------------------------------------- actions
    def test_signal(self) -> None:
        if self.recorder.status in ACTIVE_STATES:
            dialogs.info(self.root, self, "dlg.warn", self.t("msg.busy"), kind="warn")
            return
        device = self._selected_device()
        if device is None:
            dialogs.info(self.root, self, "dlg.warn", self.t("msg.no_device"), kind="warn")
            return
        self.test_btn.set_enabled(False)

        def worker():
            try:
                level = self.recorder.probe_level(device, 1.2)
                error = None
            except Exception as exc:
                level, error = 0.0, str(exc)
            self.post(lambda: self._test_done(level, error))

        threading.Thread(target=worker, daemon=True).start()

    def _test_done(self, level: float, error: Optional[str]) -> None:
        self.test_btn.set_enabled(True)
        if error:
            dialogs.error(self.root, self, "dlg.error", self.t("msg.test_error", err=error))
            return
        self.meter.set_level(level)
        if level >= 1.0:
            dialogs.info(self.root, self, "dlg.info",
                         self.t("msg.test_ok", pct=int(level)), kind="success")
        else:
            dialogs.info(self.root, self, "dlg.warn", self.t("msg.test_fail"), kind="warn")

    def paste_link(self) -> None:
        try:
            self.url_var.set(self.root.clipboard_get().strip())
        except Exception:
            pass

    def browse_directory(self) -> None:
        current = self.dir_var.get().strip()
        initial = current if current and os.path.exists(current) else default_output_dir()
        chosen = filedialog.askdirectory(parent=self.root, initialdir=initial,
                                        title=self.t("dir.label"))
        if chosen:
            self.dir_var.set(os.path.normpath(chosen))

    def open_folder(self) -> None:
        target = self.dir_var.get().strip()
        if target and os.path.isdir(target):
            try:
                os.startfile(target)
            except Exception as exc:
                dialogs.error(self.root, self, "dlg.error", str(exc))
        else:
            dialogs.info(self.root, self, "dlg.info", self.t("msg.folder_missing"))

    def open_virtual_desktop(self) -> None:
        try:
            import subprocess
            subprocess.Popen("explorer.exe shell:::{3080F90E-D7AD-11D9-BD98-0000947B0257}")
        except Exception:
            pass
        dialogs.info(self.root, self, "vdesk.title", self.t("vdesk.body"), body_is_key=False)

    def open_trim_dialog(self) -> None:
        initial = self.dir_var.get().strip()
        if not os.path.isdir(initial):
            initial = default_output_dir()
        path = filedialog.askopenfilename(
            parent=self.root, initialdir=initial, title=self.t("file.choose"),
            filetypes=[(self.t("file.media"), "*.mp4 *.mp3 *.wav *.mkv *.m4a *.webm"),
                       (self.t("file.all"), "*.*")])
        if path:
            self.open_trim(path)

    def open_trim(self, path: str) -> None:
        dialogs.TrimDialog(self.root, self, path, on_saved=self._on_saved)

    def _on_saved(self, path: str) -> None:
        if path and os.path.exists(path):
            size = os.path.getsize(path) / (1024 * 1024)
            self.info_lbl.set_literal(f"{size:.2f} MB")
            try:
                import subprocess
                subprocess.Popen(["explorer.exe", f"/select,{os.path.normpath(path)}"])
            except Exception:
                pass

    def show_about(self) -> None:
        dialogs.AboutDialog(self.root, self).show()

    def check_updates(self) -> None:
        self.update_btn.set_enabled(False)
        self.footer_status.set_key("update.checking")

        def worker():
            info = updater.fetch_latest(GITHUB_REPO, VERSION_TAG)
            self.post(lambda: self._update_done(info))

        threading.Thread(target=worker, daemon=True).start()

    def _update_done(self, info) -> None:
        self.update_btn.set_enabled(True)
        self.footer_status.set_literal("")
        if not info.ok:
            dialogs.info(self.root, self, "dlg.warn", self.t("update.error", err=info.error or ""),
                         kind="warn")
            return
        if info.newer:
            body = self.t("update.available", latest=info.latest, current=VERSION_TAG)
            if info.notes:
                body += "\n\n" + info.notes.strip()[:600]
            dlg = dialogs.MessageDialog(
                self.root, self, "update.title",
                body, kind="info",
                buttons=(("btn.close", "neutral", "close"), ("update.open", "primary", "open")))
            if dlg.show() == "open":
                webbrowser.open(info.url or RELEASES_URL)
        else:
            dialogs.info(self.root, self, "dlg.info", self.t("update.latest", v=VERSION_TAG),
                         kind="success")

    # -------------------------------------------------------------- recording
    def start_recording(self) -> None:
        if self.recorder.status in ACTIVE_STATES:
            dialogs.info(self.root, self, "dlg.warn", self.t("msg.busy"), kind="warn")
            return
        directory = self.dir_var.get().strip()
        if not directory:
            dialogs.info(self.root, self, "dlg.warn", self.t("msg.no_dir"), kind="warn")
            return
        device = self._selected_device()
        if device is None:
            dialogs.info(self.root, self, "dlg.warn", self.t("msg.no_device"), kind="warn")
            return
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as exc:
            dialogs.error(self.root, self, "dlg.error", str(exc))
            return

        url = self.url_var.get().strip()
        if url and self.auto_open_var.get():
            if not url.lower().startswith(("http://", "https://")):
                url = "https://" + url
            try:
                webbrowser.open(url)
            except Exception:
                pass

        prefix = "تسجيل" if self._lang == "ar" else "Meeting"
        try:
            self.recorder.start(mode=self.mode_var.get(), directory=directory,
                                device=device, name_prefix=prefix)
        except engine.RecorderError as exc:
            dialogs.error(self.root, self, "dlg.error", self.t("msg.start_failed", err=str(exc)))
            self._render(self.recorder.snapshot())
            return

        self._stop_requested = False
        self._error_reported = False
        self._persist()
        if self.auto_mini_var.get():
            self.show_minibar()
        self._render(self.recorder.snapshot())

    def toggle_pause(self) -> None:
        status = self.recorder.status
        if status == "recording":
            self.recorder.pause()
        elif status == "paused":
            self.recorder.resume()
        self._render(self.recorder.snapshot())

    def stop_recording(self) -> None:
        if self.recorder.status not in ("recording", "paused"):
            return
        if self._stop_requested:
            return
        self._stop_requested = True
        self.status_chip.set_key("status.finishing")
        self.status_chip.set_tone("busy")

        def worker():
            self.recorder.stop()

        self._stop_thread = threading.Thread(target=worker, daemon=True)
        self._stop_thread.start()

    def mute_alarm(self) -> None:
        self.recorder.mute_alarm()
        self.alert_lbl.set_key("alarm.muted")
        self.alert_lbl.configure(fg=self.colors["warn"])
        self.mute_btn.pack_forget()

    # ----------------------------------------------------------------- minibar
    def show_minibar(self) -> None:
        if self.minibar is not None:
            return
        try:
            self.minibar = MiniBar(self)
            self.minibar.set_mode(self.mode_var.get())
            self.root.withdraw()
        except Exception as exc:
            self.log(f"[minibar] {exc}")
            self.minibar = None
            try:
                self.root.deiconify()
            except Exception:
                pass

    def restore_from_minibar(self) -> None:
        if self.minibar is not None:
            try:
                self.minibar.destroy()
            except Exception:
                pass
            self.minibar = None
        try:
            self.root.deiconify()
            self.root.lift()
        except Exception:
            pass

    # ------------------------------------------------------------------- poll
    def _on_destroy_root(self, event) -> None:
        if getattr(event, "widget", None) is not self.root:
            return
        self._closing = True
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _poll(self) -> None:
        self._after_id = None
        if self._closing or not _alive(self.root):
            return
        try:
            while True:
                fn = self.queue.get_nowait()
                try:
                    fn()
                except Exception as exc:
                    self.log(f"[ui] {exc}")
        except queue.Empty:
            pass
        try:
            self._render(self.recorder.snapshot())
        except Exception as exc:
            self.log(f"[poll] {exc}")
        if not self._closing and _alive(self.root):
            self._after_id = self.root.after(250, self._poll)

    def _sync_start_button(self) -> None:
        mode = self.mode_var.get()
        self.start_btn.set_key("btn.start.audio" if mode == "audio" else "btn.start.video")
        self.start_btn.set_tone("primary" if mode == "video" else "success")

    def _render(self, snap) -> None:
        colours = self.colors
        # ---- status pill
        if snap.status == "recording":
            key = "status.recording.audio" if snap.mode == "audio" else "status.recording.video"
            self.status_chip.set_key(key)
            self.status_chip.set_tone("recording")
        else:
            key, tone = STATUS_STYLE.get(snap.status, STATUS_STYLE["idle"])
            self.status_chip.set_key(key)
            self.status_chip.set_tone(tone)

        # ---- timer + meter
        timer_text = engine.format_duration(snap.elapsed)
        if timer_text != self._timer_text:
            self._timer_text = timer_text
            self.timer_lbl.configure(text=timer_text)
        self.meter.set_level(snap.level, snap.alert)

        # ---- size / format
        if snap.file_size:
            ext = "MP4" if snap.mode == "video" else "MP3"
            self.info_lbl.set_literal(
                self.t("monitor.info", size=f"{snap.file_size / (1024 * 1024):.1f}", fmt=ext))
        elif snap.status == "idle":
            self.info_lbl.set_literal("")

        # ---- silence alarm
        self._render_alert(snap)

        # ---- enablement
        active = snap.status in ACTIVE_STATES
        recording = snap.status in ("recording", "paused")
        self.start_btn.set_enabled(not active)
        self.pause_btn.set_enabled(recording)
        self.stop_btn.set_enabled(recording)
        self.test_btn.set_enabled(not active)
        self.refresh_btn.set_enabled(not active)
        self.trim_btn.set_enabled(not active)
        combo_state = "disabled" if active else "readonly"
        if str(self.device_combo.combo.cget("state")) != combo_state:
            self.device_combo.combo.configure(state=combo_state)
        entry_state = "disabled" if active else "normal"
        if str(self.dir_field.entry.cget("state")) != entry_state:
            self.dir_field.entry.configure(state=entry_state)

        if snap.status == "paused":
            self.pause_btn.set_key("btn.resume")
            self.pause_btn.set_icon("▶")
            self.pause_btn.set_tone("primary")
        else:
            self.pause_btn.set_key("btn.pause")
            self.pause_btn.set_icon("❚❚")
            self.pause_btn.set_tone("neutral")
        self._sync_start_button()
        if snap.notice:
            hint, colour = self.t("notice.audio_reconnect"), self.colors["warn"]
        elif active:
            hint, colour = "", self.colors["text_faint"]
        else:
            hint, colour = self.t("monitor.idle_hint"), self.colors["text_faint"]
        if self.hint_lbl.cget("text") != hint:
            self.hint_lbl.configure(text=hint, fg=colour)

        # ---- floating bar
        if self.minibar is not None:
            try:
                self.minibar.update_state(engine.format_duration(snap.elapsed),
                                          snap.status == "paused", snap.alert,
                                          snap.alarm_muted)
            except Exception:
                self.minibar = None

        # ---- stop completion
        if self._stop_requested and snap.status in ("done", "error"):
            self._stop_requested = False
            self._after_stop(snap)
        elif snap.status == "error" and not self._stop_requested and not self._error_reported:
            self._error_reported = True
            self._after_stop(snap)

    def _set_border(self, colour: str, thickness: int) -> None:
        state = (colour, thickness)
        if state != self._border_state:
            self._border_state = state
            self.monitor_card.configure(highlightbackground=colour, highlightthickness=thickness)

    def _render_alert(self, snap) -> None:
        colours = self.colors
        alert = snap.alert
        if alert == "critical":
            self._flash = not self._flash
            border = colours["danger"] if self._flash else colours["danger_press"]
            self._set_border(border, 2)
            self.alert_lbl.set_key("alert.critical", sec=int(snap.silence))
            self.alert_lbl.configure(fg=colours["danger"])
            if not snap.alarm_muted:
                if not self.mute_btn.winfo_ismapped():
                    self.mute_btn.pack(side=self.other, padx=(px(8), 0) if self.rtl else (px(8), 0))
                now = time.monotonic()
                if now - self._last_beep >= 2.0:
                    self._last_beep = now
                    try:
                        import winsound
                        winsound.MessageBeep(winsound.MB_ICONHAND)
                    except Exception:
                        pass
            elif self.mute_btn.winfo_ismapped():
                self.mute_btn.pack_forget()
            self._prev_alert = "critical"
        elif alert == "warn":
            self._set_border(colours["warn"], 2)
            self.alert_lbl.set_key("alert.warn", sec=int(snap.silence))
            self.alert_lbl.configure(fg=colours["warn"])
            if self.mute_btn.winfo_ismapped() and snap.alarm_muted:
                self.mute_btn.pack_forget()
            self._prev_alert = "warn"
        else:
            self._set_border(colours["border"], 1)
            if self._prev_alert == "critical" and snap.status == "recording":
                self._recovered_until = time.monotonic() + 3.0
            if time.monotonic() < self._recovered_until:
                self.alert_lbl.set_key("alert.recovered")
                self.alert_lbl.configure(fg=colours["success"])
            else:
                self.alert_lbl.set_literal("")
            if self.mute_btn.winfo_ismapped():
                self.mute_btn.pack_forget()
            self._prev_alert = "none"

    def _after_stop(self, snap) -> None:
        self.restore_from_minibar()
        if snap.status == "error" or snap.error:
            dialogs.error(self.root, self, "dlg.error",
                          self.t("msg.save_failed", err=snap.error or ""))
            self._render(self.recorder.snapshot())
            return
        path = snap.output_path
        if not path or not os.path.exists(path):
            dialogs.error(self.root, self, "dlg.error", self.t("msg.save_failed", err="file missing"))
            return
        if dialogs.confirm(self.root, self, "msg.saved.title",
                           self.t("msg.saved.body", name=os.path.basename(path))):
            self.open_trim(path)
        else:
            self._on_saved(path)

    # ------------------------------------------------------------------ close
    def _on_close(self) -> None:
        snap = self.recorder.snapshot()
        if snap.status in ("recording", "paused"):
            if not dialogs.confirm(self.root, self, "msg.exit.title", self.t("msg.exit.body")):
                return
            self._closing = True
            try:
                self.recorder.stop()
            except Exception as exc:
                self.log(f"[close] {exc}")
        elif snap.status == "finishing" and self._stop_thread is not None:
            self._closing = True
            self._stop_thread.join(60)
        self._persist()
        try:
            if self.minibar is not None:
                self.minibar.destroy()
        except Exception:
            pass
        self.root.destroy()


def _alive(widget) -> bool:
    try:
        return bool(widget.winfo_exists())
    except Exception:
        return False

