# -*- coding: utf-8 -*-
"""Resource lookup + runtime configuration persistence.

Bug fixed vs v1:
  * config was written with ``open(path, "w")`` and ``ensure_ascii=False`` on a
    Windows machine whose default codec is cp1252 -> ``UnicodeEncodeError`` for
    any Arabic folder path, silently swallowed by ``except: pass`` so the app
    never remembered settings.  We now always use UTF-8 and an atomic replace.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import dataclass, field, asdict
from typing import Any, Dict

APP_DIRNAME = "EasyRecord"


def resource_dir() -> str:
    """Directory that holds bundled assets (works frozen and from source)."""
    base = getattr(sys, "_MEIPASS", None)
    if base and os.path.isdir(base):
        return base
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def asset_path(*parts: str) -> str:
    return os.path.join(resource_dir(), "assets", *parts)


def app_dir() -> str:
    return os.path.join(os.path.expanduser("~"), ".easy_record")


def config_path() -> str:
    return os.path.join(app_dir(), "config.json")


def default_output_dir() -> str:
    """Preferred recordings folder, falling back to Documents/Desktop."""
    for candidate in (r"D:\DBA_Records",):
        try:
            os.makedirs(candidate, exist_ok=True)
            return candidate
        except Exception:
            pass
    home = os.path.expanduser("~")
    for candidate in (
        os.path.join(home, "Documents", "Easy Record"),
        os.path.join(home, "Desktop", "Easy Record"),
        os.path.join(tempfile.gettempdir(), "Easy Record"),
    ):
        try:
            os.makedirs(candidate, exist_ok=True)
            return candidate
        except Exception:
            continue
    return home


@dataclass
class Config:
    mode: str = "video"            # video | audio
    directory: str = field(default_factory=default_output_dir)
    lang: str = "ar"               # ar | en
    theme: str = "day"             # day | night
    auto_open: bool = True
    auto_mini: bool = True
    confirm_trim: bool = True

    # ---------------------------------------------------------------- loading
    @classmethod
    def load(cls, path: str | None = None) -> "Config":
        path = path or config_path()
        cfg = cls()
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw: Dict[str, Any] = json.load(fh)
        except Exception:
            return cfg
        if not isinstance(raw, dict):
            return cfg

        # Tolerate the legacy v1 schema ({"mode": ..., "dir": ...}).
        if isinstance(raw.get("directory", raw.get("dir")), str):
            cfg.directory = raw.get("directory") or raw.get("dir")
        if raw.get("mode") in ("video", "audio"):
            cfg.mode = raw["mode"]
        if raw.get("lang") in ("ar", "en"):
            cfg.lang = raw["lang"]
        if raw.get("theme") in ("day", "night"):
            cfg.theme = raw["theme"]
        for attr in ("auto_open", "auto_mini", "confirm_trim"):
            if isinstance(raw.get(attr), bool):
                setattr(cfg, attr, raw[attr])
        if not cfg.directory:
            cfg.directory = default_output_dir()
        return cfg

    # ---------------------------------------------------------------- saving
    def save(self, path: str | None = None) -> bool:
        path = path or config_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            payload = json.dumps(asdict(self), ensure_ascii=False, indent=2)
            tmp = f"{path}.tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
            return True
        except Exception:
            return False
