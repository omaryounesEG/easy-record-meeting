# -*- coding: utf-8 -*-
"""Rewrite the GitHub release page: name, features, free license, icon, AR/EN, keywords."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

TOKEN = os.environ["GH_TOKEN_LOCAL"]
HERE = r"H:/Meeting_REC"
API = "https://api.github.com/repos/omaryounesEG/easy-record-meeting"
TAG = os.environ.get("RELEASE_TAG", "v2.0.1")
NAME = "Easy Record Meeting — مسجّل الاجتماعات الذكي"


def call(url: str, method: str = "GET", payload: dict | None = None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "easyrec-release")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw) if raw else {}
        except Exception:
            return exc.code, {"message": raw[:200].decode("utf-8", "replace")}


def main() -> None:
    body = open(os.path.join(HERE, "docs", "RELEASE_BODY.md"), encoding="utf-8").read()

    status, rel = call(f"{API}/releases/tags/{TAG}")
    if status != 200:
        raise SystemExit(f"release {TAG} not found: {status} {rel.get('message')}")

    status, updated = call(f"{API}/releases/{rel['id']}", "PATCH",
                           {"name": NAME, "body": body})
    print("patch:", status, updated.get("name") or updated.get("message"))

    status, check = call(f"{API}/releases/{rel['id']}")
    print("read back name:", check["name"])
    print("body chars:", len(check["body"]),
          "| has icon:", "icon_512.png" in check["body"],
          "| has MIT:", "MIT" in check["body"],
          "| has keywords:", "meeting recorder" in check["body"] and "مسجّل اجتماعات" in check["body"])
    print("tag:", check["tag_name"], "| assets:", [(a["name"], a["size"]) for a in check["assets"]])
    print("URL", check["html_url"])


if __name__ == "__main__":
    main()
