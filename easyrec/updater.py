# -*- coding: utf-8 -*-
"""GitHub release check used by the “Update” button.

Pure stdlib (urllib) so it works in a frozen build without extra packages, and
completely side-effect free: it only reads the public Releases API.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional, Tuple

UA = "EasyRecord-Meeting-Updater"
API = "https://api.github.com/repos/{repo}/releases/latest"


@dataclass
class UpdateInfo:
    ok: bool
    current: str = ""
    latest: str = ""
    url: str = ""
    notes: str = ""
    published: str = ""
    error: Optional[str] = None

    @property
    def newer(self) -> bool:
        return self.ok and is_newer(self.latest, self.current)


def parse_version(text: str) -> Tuple[int, ...]:
    """``v2.1.0-beta`` -> (2, 1, 0). Non-numeric suffixes are ignored."""
    raw = (text or "").strip().lstrip("vV")
    numbers = re.findall(r"\d+", raw.split("-")[0].split("+")[0])
    if not numbers:
        return (0,)
    return tuple(int(n) for n in numbers)


def is_newer(latest: str, current: str) -> bool:
    a, b = parse_version(latest), parse_version(current)
    length = max(len(a), len(b))
    a += (0,) * (length - len(a))
    b += (0,) * (length - len(b))
    return a > b


def fetch_latest(repo: str, current: str = "", timeout: float = 8.0) -> UpdateInfo:
    request = urllib.request.Request(
        API.format(repo=repo),
        headers={"User-Agent": UA, "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return UpdateInfo(False, current=current,
                              error="no published release yet (404)")
        if exc.code in (403, 429):
            return UpdateInfo(False, current=current,
                              error=f"GitHub rate limit ({exc.code})")
        return UpdateInfo(False, current=current, error=f"HTTP {exc.code}")
    except Exception as exc:                    # offline, DNS, TLS, timeout
        return UpdateInfo(False, current=current, error=str(exc) or exc.__class__.__name__)

    tag = payload.get("tag_name") or payload.get("name") or ""
    return UpdateInfo(
        ok=bool(tag),
        current=current,
        latest=tag,
        url=payload.get("html_url") or "",
        notes=(payload.get("body") or "")[:4000],
        published=payload.get("published_at") or "",
        error=None if tag else "release has no tag",
    )
