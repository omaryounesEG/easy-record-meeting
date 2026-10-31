# -*- coding: utf-8 -*-
"""Soft, rounded UI primitives drawn on Tk canvases.

Tk's native buttons cannot be rounded, so every interactive control here is a
Canvas that paints a rounded rectangle and handles hover / press / disabled
states itself.  All widgets implement ``apply_theme()`` and ``retranslate()`` so
the day/night switch and the AR/EN switch are instant and lossless — no window
is rebuilt, so a recording in progress is never disturbed.
"""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from typing import Callable, Iterable, Optional, Sequence

SCALE = 1.0


def set_scale(value: float) -> None:
    global SCALE
    SCALE = max(0.75, min(3.0, float(value or 1.0)))


def px(value: float) -> int:
    return max(1, int(round(float(value) * SCALE)))


def round_points(x1: float, y1: float, x2: float, y2: float, r: float,
                 steps: int = 10) -> list:
    """Flat point list for a rounded rectangle with true circular corners."""
    r = max(0.0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    if r <= 0.5:
        return [x1, y1, x2, y1, x2, y2, x1, y2]
    points: list = []
    corners = (
        (x2 - r, y1 + r, -90.0),
        (x2 - r, y2 - r, 0.0),
        (x1 + r, y2 - r, 90.0),
        (x1 + r, y1 + r, 180.0),
    )
    for cx, cy, start in corners:
        for i in range(steps + 1):
            angle = math.radians(start + 90.0 * i / steps)
            points.extend((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return points


def rounded_rect(canvas: tk.Canvas, x1, y1, x2, y2, r, **kwargs):
    outline = kwargs.pop("outline", "")
    width = kwargs.pop("width", 0)
    return canvas.create_polygon(
        round_points(x1, y1, x2, y2, r), smooth=False,
        outline=outline or kwargs.get("fill", ""), width=width, **kwargs)


class Themed:
    """Mixin: widgets register themselves and react to theme/language changes."""

    app = None
    key: Optional[str] = None
    key_kwargs: dict = {}

    def attach(self, app) -> None:
        self.app = app
        app.widgets.append(self)
        try:
            self.bind("<Destroy>", self._on_destroy, add="+")
        except Exception:
            pass

    def _on_destroy(self, event) -> None:
        if getattr(event, "widget", None) is not self:
            return
        try:
            self.app.widgets.remove(self)
        except (ValueError, AttributeError):
            pass

    # default no-ops so the app can iterate every widget uniformly
    def apply_theme(self) -> None:      # pragma: no cover - overridden
        pass

    def retranslate(self) -> None:      # pragma: no cover - overridden
        pass

    def text(self) -> str:
        if self.key and self.app is not None:
            return self.app.t(self.key, **self.key_kwargs)
        return getattr(self, "literal", "") or ""


# ----------------------------------------------------------------- text label
KIND_STYLE = {
    # kind: (palette colour, size, weight, anchor default)
    "title": ("text", 20, "bold"),
    "subtitle": ("text_muted", 10, None),
    "section": ("text_muted", 9.5, "bold"),
    "body": ("text", 10.5, None),
    "strong": ("text", 10.5, "bold"),
    "muted": ("text_muted", 9.5, None),
    "faint": ("text_faint", 9, None),
    "accent": ("primary", 10, "bold"),
    "success": ("success", 10, "bold"),
    "danger": ("danger", 10, "bold"),
    "mono": ("text", 11, "bold"),
    "timer": ("text", 34, "bold"),
}


class TFrame(tk.Frame, Themed):
    """Themed container; ``role`` picks the palette key for its background."""

    ROLES = {"surface": "surface", "bg": "bg", "alt": "surface_alt",
             "sunken": "surface_sunken", "border": "border", "card": "surface"}

    def __init__(self, master, app, role: str = "surface", **kwargs):
        self.role = role if role in self.ROLES else "surface"
        colours = app.colors
        kwargs.pop("bg", None)
        tk.Frame.__init__(self, master, bg=colours[self.ROLES[self.role]], **kwargs)
        self.attach(app)

    def colour(self) -> str:
        return self.app.colors[self.ROLES[self.role]]

    def apply_theme(self) -> None:
        try:
            self.configure(bg=self.colour())
        except Exception:
            pass

    def retranslate(self) -> None:
        pass


class TLabel(tk.Label, Themed):
    def __init__(self, master, app, key: Optional[str] = None, text: Optional[str] = None,
                 kind: str = "body", size: Optional[float] = None, weight: Optional[str] = None,
                 mono: bool = False, anchor: Optional[str] = None,
                 justify: Optional[str] = None, wraplength: int = 0, **kwargs):
        self.kind = kind if kind in KIND_STYLE else "body"
        self.size = size
        self.weight = weight
        self.mono = mono or self.kind == "timer"
        self.key = key
        self.literal = text or ""
        self.key_kwargs = {}
        colours = app.colors
        if anchor is None:
            anchor = "e" if app.rtl else "w"
        if justify is None:
            justify = "right" if app.rtl else "left"
        tk.Label.__init__(
            self, master, text=self.initial_text(app), bg=colours["bg"],
            fg=colours[KIND_STYLE[self.kind][0]], anchor=anchor, justify=justify,
            wraplength=wraplength, font=self.build_font(app), bd=0,
            highlightthickness=0, **kwargs)
        self.attach(app)
        self.apply_theme()

    # ------------------------------------------------------------------ fonts
    def build_font(self, app) -> tuple:
        size = self.size if self.size is not None else KIND_STYLE[self.kind][1]
        weight = self.weight if self.weight is not None else KIND_STYLE[self.kind][2]
        family = app.fonts["mono"] if self.mono else app.fonts["body"]
        return (family, px(size), weight) if weight else (family, px(size))

    def initial_text(self, app) -> str:
        if self.key:
            return app.t(self.key, **self.key_kwargs)
        return self.literal

    # ------------------------------------------------------------------ state
    def set_key(self, key: Optional[str], **kwargs) -> None:
        if key == self.key and kwargs == self.key_kwargs:
            return
        self.key = key
        self.key_kwargs = kwargs
        self.retranslate()

    def set_literal(self, text: str) -> None:
        self.key = None
        self.literal = text
        self.configure(text=text)

    def apply_theme(self) -> None:
        colours = self.app.colors
        parent_bg = self._parent_bg(colours)
        self.configure(
            bg=parent_bg,
            fg=colours[KIND_STYLE[self.kind][0]],
            font=self.build_font(self.app),
            activebackground=parent_bg,
        )

    def _parent_bg(self, colours) -> str:
        try:
            bg = self.master.cget("bg")
            if isinstance(bg, str) and bg:
                return bg
        except Exception:
            pass
        return colours["bg"]

    def retranslate(self) -> None:
        self.configure(text=self.initial_text(self.app))


# ------------------------------------------------------------------ chip pill
class Chip(tk.Canvas, Themed):
    def __init__(self, master, app, key: Optional[str] = None, text: Optional[str] = None,
                 tone: str = "muted", size: float = 9.5, pad_x: float = 12,
                 pad_y: float = 5, dot: bool = True):
        self.key = key
        self.literal = text or ""
        self.tone = tone
        self.size = size
        self.pad_x, self.pad_y = pad_x, pad_y
        self.dot = dot
        self.key_kwargs = {}
        self._value = ""
        tk.Canvas.__init__(self, master, bg=app.colors["surface"], highlightthickness=0, bd=0)
        self.attach(app)
        self._resize()
        self.apply_theme()

    def set_tone(self, tone: str) -> None:
        if tone == self.tone:
            return
        self.tone = tone
        self.apply_theme()

    def set_key(self, key: Optional[str], **kwargs) -> None:
        if key == self.key and kwargs == self.key_kwargs:
            return
        self.key = key
        self.key_kwargs = kwargs
        self.retranslate()

    def set_value(self, value: str) -> None:
        self._value = value
        self.apply_theme()

    def _font(self) -> tuple:
        return (self.app.fonts["body"], px(self.size), "bold")

    def _measure(self) -> tuple:
        font = tkfont.Font(family=self.app.fonts["body"], size=px(self.size), weight="bold")
        text = self.text()
        width = font.measure(text) + px(self.pad_x) * 2 + (px(14) if self.dot else 0)
        height = font.metrics("linespace") + px(self.pad_y) * 2
        return width, height, text

    def _resize(self) -> None:
        width, height, _ = self._measure()
        self.configure(width=width, height=height)

    def apply_theme(self) -> None:
        colours = self.app.colors
        try:
            self.configure(bg=self.master.cget("bg"))
        except Exception:
            self.configure(bg=colours["surface"])
        tone = self.tone
        bg_map = {
            "idle": ("chip", "text_muted"),
            "recording": ("danger_soft", "danger"),
            "paused": ("warn_soft", "warn"),
            "success": ("success_soft", "success"),
            "busy": ("primary_soft", "primary"),
            "muted": ("chip", "text_muted"),
            "danger": ("danger_soft", "danger"),
        }
        bg_key, fg_key = bg_map.get(tone, bg_map["muted"])
        bg = colours[bg_key]
        fg = colours[fg_key]
        self._resize()
        self.delete("all")
        width = int(self.cget("width"))
        height = int(self.cget("height"))
        rounded_rect(self, 1, 1, width - 1, height - 1, height / 2 - 1, fill=bg)
        text = self.text()
        x = width / 2
        if self.dot:
            r = px(3)
            dot_x = px(self.pad_x) * 0.6
            self.create_oval(dot_x - r, height / 2 - r, dot_x + r, height / 2 + r,
                             fill=fg, outline=fg)
            x = width / 2 + px(6)
        self.create_text(x, height / 2, text=text, fill=fg, font=self._font(),
                         anchor="center")
        try:
            self.master.configure(bg=self.master.cget("bg"))
        except Exception:
            pass

    def retranslate(self) -> None:
        self.apply_theme()


# --------------------------------------------------------------- round button
TONES = {
    # tone: (fill, hover, press, text colour key)
    "primary": ("primary", "primary_hover", "primary_press", "on_primary"),
    "success": ("success", "success_hover", "success_press", "on_success"),
    "danger": ("danger", "danger_hover", "danger_press", "on_danger"),
    "warn": ("warn", "warn_hover", "warn_press", "on_warn"),
    "neutral": ("neutral", "neutral_hover", "neutral_press", "neutral_text"),
    "soft": ("primary_soft", "surface_alt", "surface_sunken", "primary"),
    "ghost": ("surface", "surface_alt", "surface_sunken", "text_muted"),
}


class RoundButton(tk.Canvas, Themed):
    def __init__(self, master, app, key: Optional[str] = None, text: Optional[str] = None,
                 command: Optional[Callable] = None, tone: str = "primary",
                 icon: str = "", size: float = 10.5, bold: bool = True,
                 height: float = 42, radius: Optional[float] = None,
                 pad_x: float = 18, width: Optional[float] = None,
                 tooltip: Optional[str] = None):
        self.key = key
        self.literal = text or ""
        self.command = command
        self.tone = tone
        self.icon = icon
        self.size = size
        self.bold = bold
        self.base_height = height
        self.radius = radius
        self.pad_x = pad_x
        self.fixed_width = width
        self.tooltip_key = tooltip
        self.key_kwargs = {}
        self._enabled = True
        self._hover = False
        self._pressed = False
        self._expanded = width is None
        self._stretched = False

        colours = app.colors
        tk.Canvas.__init__(self, master, bg=colours["bg"], highlightthickness=0,
                           bd=0, height=px(height), cursor="hand2")
        self.attach(app)
        self.bind("<Configure>", lambda _e: self._redraw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.apply_theme()

    # ------------------------------------------------------------------ sizing
    def _font(self) -> tuple:
        family = self.app.fonts["body"]
        return (family, px(self.size), "bold") if self.bold else (family, px(self.size))

    def _label(self) -> str:
        text = self.text()
        return f"{self.icon}  {text}" if self.icon else text

    def _desired_width(self) -> int:
        if self.fixed_width:
            return px(self.fixed_width)
        font = tkfont.Font(family=self.app.fonts["body"], size=px(self.size),
                           weight="bold" if self.bold else "normal")
        return font.measure(self._label()) + px(self.pad_x) * 2

    def _redraw(self) -> None:
        colours = self.app.colors
        fill_key, hover_key, press_key, text_key = TONES.get(self.tone, TONES["primary"])
        if not self._enabled:
            fill = colours["disabled_bg"]
            fg = colours["disabled_text"]
        else:
            key = press_key if self._pressed else (hover_key if self._hover else fill_key)
            fill = colours[key]
            fg = colours[text_key]
            # "ghost"/"soft" look needs a hairline so it reads as a control
            if self.tone in ("ghost", "soft") and not (self._hover or self._pressed):
                fg = colours[text_key]
        desired = self._desired_width()
        width = self.winfo_width()
        if width <= 1:
            width = desired
        width = max(width, desired)
        height = max(int(self.winfo_height()), px(self.base_height))
        radius = px(self.radius if self.radius is not None else min(height / 2, 14))
        self.delete("all")
        rounded_rect(self, 0.5, 0.5, width - 0.5, height - 0.5, radius, fill=fill)
        if self.tone in ("ghost", "soft") and not self._pressed:
            rounded_rect(self, 0.5, 0.5, width - 0.5, height - 0.5, radius,
                         fill="", outline=colours["border"], width=1)
        self.create_text(width / 2, height / 2, text=self._label(), fill=fg,
                         font=self._font(), anchor="center")
        try:
            self.configure(bg=self.master.cget("bg"), height=height,
                           width=desired if not self._stretched else width)
        except Exception:
            pass

    # ------------------------------------------------------------------- events
    def _on_enter(self, _event=None):
        if not self._enabled:
            return
        self._hover = True
        self._redraw()

    def _on_leave(self, _event=None):
        self._hover = self._pressed = False
        self._redraw()

    def _on_press(self, _event=None):
        if not self._enabled:
            return
        self._pressed = True
        self._redraw()

    def _on_release(self, event=None):
        if not self._enabled:
            return
        was_inside = True
        if event is not None:
            was_inside = 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height()
        self._pressed = False
        self._redraw()
        if was_inside and self.command:
            self.command()

    # ------------------------------------------------------------------- public
    def set_enabled(self, enabled: bool) -> None:
        if bool(enabled) == self._enabled:
            return
        self._enabled = bool(enabled)
        try:
            self.configure(cursor="hand2" if enabled else "arrow")
        except Exception:
            pass
        self._redraw()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_tone(self, tone: str) -> None:
        if tone == self.tone:
            return
        self.tone = tone
        self._redraw()

    def set_key(self, key: Optional[str], **kwargs) -> None:
        if key == self.key and kwargs == self.key_kwargs:
            return
        self.key = key
        self.key_kwargs = kwargs
        self.retranslate()

    def set_icon(self, icon: str) -> None:
        if icon == self.icon:
            return
        self.icon = icon
        self._redraw()

    def apply_theme(self) -> None:
        self._redraw()
        try:
            self.configure(bg=self.master.cget("bg"))
        except Exception:
            pass

    def retranslate(self) -> None:
        self._redraw()


# ---------------------------------------------------------------- toggle switch
class ToggleSwitch(tk.Canvas, Themed):
    def __init__(self, master, app, variable, key: Optional[str] = None,
                 text: Optional[str] = None, command: Optional[Callable] = None,
                 width: float = 44, height: float = 24):
        self.var = variable
        self.key = key
        self.literal = text or ""
        self.command = command
        self.key_kwargs = {}
        self.track_w, self.track_h = width, height
        tk.Canvas.__init__(self, master, bg=app.colors["bg"], highlightthickness=0,
                           bd=0, width=px(width), height=px(height), cursor="hand2")
        self.attach(app)
        self.bind("<ButtonRelease-1>", self._toggle)
        self.apply_theme()

    def _toggle(self, _event=None):
        self.var.set(not bool(self.var.get()))
        self.apply_theme()
        if self.command:
            self.command()

    def apply_theme(self) -> None:
        colours = self.app.colors
        on = bool(self.var.get())
        width, height = px(self.track_w), px(self.track_h)
        self.configure(bg=self.master.cget("bg"), width=width, height=height)
        self.delete("all")
        track = colours["primary"] if on else colours["track"]
        rounded_rect(self, 1, 1, width - 1, height - 1, height / 2, fill=track)
        pad = px(3)
        knob = height - pad * 2
        x1 = width - knob - pad if on else pad
        self.create_oval(x1, pad, x1 + knob, pad + knob,
                         fill=colours["surface"] if on else colours["surface"],
                         outline=track)

    def retranslate(self) -> None:
        self.apply_theme()


# ------------------------------------------------------------ segmented control
class Segmented(tk.Canvas, Themed):
    def __init__(self, master, app, options: Sequence[tuple], value: str,
                 command: Optional[Callable[[str], None]] = None,
                 size: float = 9.5, height: float = 32, pad_x: float = 12):
        self.options = list(options)          # [(value, i18n_key), ...]
        self.value = value
        self.command = command
        self.size = size
        self.base_height = height
        self.pad_x = pad_x
        self._hover_index = -1
        self._rects: list = []
        tk.Canvas.__init__(self, master, bg=app.colors["bg"], highlightthickness=0,
                           bd=0, height=px(height), cursor="hand2")
        self.attach(app)
        self.bind("<Configure>", lambda _e: self.apply_theme())
        self.bind("<ButtonRelease-1>", self._on_click)
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", lambda _e: self._set_hover(-1))
        self.apply_theme()

    def _font(self, bold=False) -> tuple:
        family = self.app.fonts["body"]
        return (family, px(self.size), "bold") if bold else (family, px(self.size))

    def _labels(self) -> list:
        return [self.app.t(key) for _value, key in self.options]

    def _measure(self) -> tuple:
        font = tkfont.Font(family=self.app.fonts["body"], size=px(self.size), weight="bold")
        widths = [font.measure(label) + px(self.pad_x) * 2 for label in self._labels()]
        return widths, max(widths) if widths else px(60)

    def apply_theme(self) -> None:
        colours = self.app.colors
        widths, total = self._measure()
        width = sum(widths) + px(4)
        height = px(self.base_height)
        self.configure(bg=self.master.cget("bg"), width=width, height=height)
        self.delete("all")
        self._rects = []
        rounded_rect(self, 1, 1, width - 1, height - 1, height / 2, fill=colours["surface_alt"])
        x = px(2)
        labels = self._labels()
        for index, ((value, _key), label, w) in enumerate(zip(self.options, labels, widths)):
            selected = value == self.value
            if selected:
                rounded_rect(self, x, px(2), x + w, height - px(2),
                             (height - px(4)) / 2, fill=colours["surface"])
            elif index == self._hover_index:
                rounded_rect(self, x, px(2), x + w, height - px(2),
                             (height - px(4)) / 2, fill=colours["chip"])
            colour = colours["text"] if selected else colours["text_muted"]
            self.create_text(x + w / 2, height / 2, text=label, fill=colour,
                             font=self._font(selected), anchor="center")
            self._rects.append((x, x + w, value))
            x += w
        if self._hover_index >= 0:
            pass

    # ------------------------------------------------------------------- events
    def _index_at(self, x: float) -> int:
        for index, (x1, x2, _value) in enumerate(self._rects):
            if x1 <= x <= x2:
                return index
        return -1

    def _on_motion(self, event):
        index = self._index_at(event.x)
        if index != self._hover_index:
            self._set_hover(index)

    def _set_hover(self, index: int) -> None:
        if index != self._hover_index:
            self._hover_index = index
            self.apply_theme()

    def _on_click(self, event):
        index = self._index_at(event.x)
        if index >= 0:
            self.set_value(self._rects[index][2])

    def set_value(self, value: str, notify: bool = True) -> None:
        if value == self.value:
            return
        self.value = value
        self.apply_theme()
        if notify and self.command:
            self.command(value)

    def apply_theme_if_needed(self) -> None:
        self.apply_theme()

    def retranslate(self) -> None:
        self.apply_theme()


# ------------------------------------------------------------------ level meter
class Meter(tk.Canvas, Themed):
    """Segmented level meter that updates in place (no per-poll redraw storm)."""

    SEGMENTS = 34

    def __init__(self, master, app, height: float = 16):
        self.base_height = height
        self._level = 0.0
        self._alert = "none"
        self._items: list = []
        self._painted: list = []
        self._geometry = (0, 0)
        tk.Canvas.__init__(self, master, height=px(height), bg=app.colors["surface"],
                           highlightthickness=0, bd=0)
        self.attach(app)
        self.bind("<Configure>", lambda _e: self._build_geometry())
        self._build_geometry()

    # ------------------------------------------------------------------ public
    def set_level(self, level: float, alert: str = "none") -> None:
        level = max(0.0, min(100.0, float(level)))
        if abs(level - self._level) < 0.5 and alert == self._alert:
            return
        self._level, self._alert = level, alert
        self._paint()

    def apply_theme(self) -> None:
        try:
            self.configure(bg=self.master.cget("bg"))
        except Exception:
            pass
        self._painted = [None] * len(self._items)
        self._paint()

    # --------------------------------------------------------------- geometry
    def _build_geometry(self) -> None:
        width = max(int(self.winfo_width()), px(200))
        height = max(int(self.winfo_height()), px(self.base_height))
        if (width, height) == self._geometry and self._items:
            return
        self._geometry = (width, height)
        colours = self.app.colors
        self.delete("all")
        self._items = []
        gap = px(2)
        seg_w = max(px(3), (width - gap * (self.SEGMENTS - 1)) / self.SEGMENTS)
        for index in range(self.SEGMENTS):
            x1 = index * (seg_w + gap)
            item = rounded_rect(self, x1, px(2), x1 + seg_w, height - px(2),
                                min(seg_w / 2, px(4)), fill=colours["meter_track"])
            self._items.append(item)
        self._painted = [None] * len(self._items)
        self._paint()

    # ------------------------------------------------------------------- paint
    def _colour_for(self, index: int, active: int) -> str:
        colours = self.app.colors
        if index >= active:
            return colours["meter_track"]
        if self._alert == "critical" or index / self.SEGMENTS >= 0.85:
            return colours["danger"]
        if index / self.SEGMENTS >= 0.6:
            return colours["warn"]
        return colours["success"]

    def _paint(self) -> None:
        active = int(round(self._level / 100.0 * self.SEGMENTS))
        for index, item in enumerate(self._items):
            colour = self._colour_for(index, active)
            if self._painted[index] != colour:
                try:
                    self.itemconfigure(item, fill=colour, outline=colour)
                except Exception:
                    pass
                self._painted[index] = colour


# ------------------------------------------------------------------- text field
class Field(tk.Frame, Themed):
    def __init__(self, master, app, textvariable=None, placeholder_key: Optional[str] = None,
                 height: float = 40, show: str = "", readonly: bool = False):
        self.key = placeholder_key
        self._readonly = readonly
        self.base_height = height
        colours = app.colors
        tk.Frame.__init__(self, master, bg=colours["surface_alt"],
                          highlightthickness=1, highlightbackground=colours["border"],
                          highlightcolor=colours["primary"])
        self.attach(app)
        self.entry = tk.Entry(self, textvariable=textvariable, bd=0, relief="flat",
                              bg=colours["surface_alt"], fg=colours["text"],
                              insertbackground=colours["primary"],
                              font=(app.fonts["body"], px(10.5)),
                              highlightthickness=0, disabledbackground=colours["disabled_bg"],
                              disabledforeground=colours["disabled_text"],
                              readonlybackground=colours["surface_alt"])
        self.entry.pack(fill="both", expand=True, padx=px(10), pady=px(7))
        self.entry.bind("<FocusIn>", lambda _e: self._focus(True))
        self.entry.bind("<FocusOut>", lambda _e: self._focus(False))
        self.apply_theme()

    def _focus(self, active: bool) -> None:
        colours = self.app.colors
        self.configure(highlightbackground=colours["primary"] if active else colours["border"])

    def set_readonly(self, readonly: bool) -> None:
        self._readonly = readonly
        self.entry.configure(state="readonly" if readonly else "normal")

    def get(self) -> str:
        return self.entry.get()

    def apply_theme(self) -> None:
        colours = self.app.colors
        self.configure(bg=colours["surface_alt"], highlightbackground=colours["border"])
        self.entry.configure(bg=colours["surface_alt"], fg=colours["text"],
                             insertbackground=colours["primary"],
                             disabledbackground=colours["disabled_bg"],
                             disabledforeground=colours["disabled_text"],
                             readonlybackground=colours["surface_alt"],
                             font=(self.app.fonts["body"], px(10.5)))

    def retranslate(self) -> None:
        pass


class TCombo(tk.Frame, Themed):
    """ttk combobox wrapped so the popdown list follows the theme too."""

    def __init__(self, master, app, textvariable=None, values: Iterable[str] = (),
                 height: float = 40):
        colours = app.colors
        tk.Frame.__init__(self, master, bg=colours["surface_alt"], highlightthickness=1,
                          highlightbackground=colours["border"])
        self.attach(app)
        self.combo = ttk.Combobox(self, textvariable=textvariable, values=list(values),
                                  state="readonly", style="Easy.TCombobox",
                                  font=(app.fonts["body"], px(10)))
        self.combo.pack(fill="both", expand=True, padx=px(6), pady=px(4))
        self.apply_theme()

    def set_values(self, values: Iterable[str]) -> None:
        self.combo["values"] = list(values)

    def apply_theme(self) -> None:
        if not self.winfo_exists():
            return
        colours = self.app.colors
        self.configure(bg=colours["surface_alt"], highlightbackground=colours["border"])
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Easy.TCombobox",
            fieldbackground=colours["surface_alt"],
            background=colours["surface_alt"],
            foreground=colours["text"],
            arrowcolor=colours["text_muted"],
            bordercolor=colours["border"],
            lightcolor=colours["surface_alt"],
            darkcolor=colours["surface_alt"],
            selectbackground=colours["primary_soft"],
            selectforeground=colours["text"],
            padding=px(4),
        )
        style.map("Easy.TCombobox",
                  fieldbackground=[("readonly", colours["surface_alt"])],
                  foreground=[("readonly", colours["text"])],
                  selectbackground=[("readonly", colours["primary_soft"])],
                  selectforeground=[("readonly", colours["text"])],
                  bordercolor=[("focus", colours["primary"])])
        self.combo.configure(style="Easy.TCombobox",
                             font=(self.app.fonts["body"], px(10)))
        # the dropdown list is a plain Tk listbox: style it globally
        self.winfo_toplevel().option_add("*TCombobox*Listbox.background", colours["surface"])
        self.winfo_toplevel().option_add("*TCombobox*Listbox.foreground", colours["text"])
        self.winfo_toplevel().option_add("*TCombobox*Listbox.selectBackground", colours["primary"])
        self.winfo_toplevel().option_add("*TCombobox*Listbox.selectForeground", "white")
        self.winfo_toplevel().option_add("*TCombobox*Listbox.font",
                                         (self.app.fonts["body"], px(10)))

    def retranslate(self) -> None:
        pass


# ------------------------------------------------------------------- card frame
class Card(tk.Frame, Themed):
    def __init__(self, master, app, title_key: Optional[str] = None,
                 hint_key: Optional[str] = None, pad: float = 14):
        colours = app.colors
        tk.Frame.__init__(self, master, bg=colours["surface"], highlightthickness=1,
                          highlightbackground=colours["border"], bd=0)
        self.attach(app)
        self.title_key, self.hint_key = title_key, hint_key
        inner = tk.Frame(self, bg=colours["surface"])
        inner.pack(fill="both", expand=True, padx=px(pad), pady=px(pad - 2))
        self.body = inner
        self.title_label: Optional[TLabel] = None
        self.hint_label: Optional[TLabel] = None
        if title_key:
            head = TFrame(inner, app, role="surface")
            head.pack(fill="x", pady=(0, px(8)))
            self.title_label = TLabel(head, app, key=title_key, kind="strong", size=11.5)
            self.title_label.pack(side="right" if app.rtl else "left")
            if hint_key:
                self.hint_label = TLabel(head, app, key=hint_key, kind="faint", size=8.5)
                self.hint_label.pack(side="right" if app.rtl else "left", padx=(0 if app.rtl else px(8), px(8) if app.rtl else 0))

    def apply_theme(self) -> None:
        colours = self.app.colors
        self.configure(bg=colours["surface"], highlightbackground=colours["border"])
        self.body.configure(bg=colours["surface"])

    def retranslate(self) -> None:
        pass


class HSep(tk.Frame, Themed):
    def __init__(self, master, app, pad: float = 0):
        tk.Frame.__init__(self, master, bg=app.colors["border"], height=1)
        self.attach(app)

    def apply_theme(self) -> None:
        self.configure(bg=self.app.colors["border"])

    def retranslate(self) -> None:
        pass


class ChoiceTile(tk.Canvas, Themed):
    """Selectable option card (used for “video + audio” vs “audio only”)."""

    def __init__(self, master, app, value: str, title_key: str, desc_key: str,
                 variable, icon: str = "", command: Optional[Callable] = None,
                 height: float = 68):
        self.value = value
        self.title_key, self.desc_key = title_key, desc_key
        self.variable = variable
        self.icon = icon
        self.command = command
        self.base_height = height
        self._hover = False
        tk.Canvas.__init__(self, master, bg=app.colors["surface"], highlightthickness=0,
                           bd=0, height=px(height), cursor="hand2")
        self.attach(app)
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self.bind("<ButtonRelease-1>", self._select)
        self.bind("<Configure>", lambda _e: self.apply_theme())
        self.apply_theme()

    def _set_hover(self, value: bool) -> None:
        if value != self._hover:
            self._hover = value
            self.apply_theme()

    def _select(self, _event=None) -> None:
        self.variable.set(self.value)
        if self.command:
            self.command(self.value)
        self.apply_theme()

    @property
    def selected(self) -> bool:
        try:
            return self.variable.get() == self.value
        except Exception:
            return False

    def apply_theme(self) -> None:
        colours = self.app.colors
        width = max(int(self.winfo_width()), px(150))
        height = max(int(self.winfo_height()), px(self.base_height))
        selected = self.selected
        fill = colours["primary_soft"] if selected else (
            colours["surface_alt"] if self._hover else colours["surface"])
        border = colours["primary"] if selected else colours["border"]
        self.delete("all")
        rounded_rect(self, 1, 1, width - 1, height - 1, px(14), fill=fill,
                     outline=border, width=2 if selected else 1)
        pad = px(14)
        title_colour = colours["primary"] if selected else colours["text"]
        title_font = (self.app.fonts["body"], px(10.5), "bold")
        desc_font = (self.app.fonts["body"], px(8.6))
        text_x = width - pad if self.app.rtl else pad
        anchor = "e" if self.app.rtl else "w"
        self.create_text(text_x, height / 2 - px(9), text=self.app.t(self.title_key),
                         fill=title_colour, font=title_font, anchor=anchor)
        self.create_text(text_x, height / 2 + px(11), text=self.app.t(self.desc_key),
                         fill=colours["text_muted"], font=desc_font, anchor=anchor)
        # radio dot
        dot_r = px(6)
        dot_x = pad + dot_r if self.app.rtl else width - pad - dot_r
        self.create_oval(dot_x - dot_r, height / 2 - dot_r, dot_x + dot_r, height / 2 + dot_r,
                         outline=colours["primary"] if selected else colours["border_strong"],
                         width=2 if selected else 1, fill=fill)
        if selected:
            self.create_oval(dot_x - dot_r / 2.2, height / 2 - dot_r / 2.2,
                             dot_x + dot_r / 2.2, height / 2 + dot_r / 2.2,
                             fill=colours["primary"], outline=colours["primary"])
        try:
            self.configure(bg=self.master.cget("bg"), height=height)
        except Exception:
            pass

    def retranslate(self) -> None:
        self.apply_theme()
