# -*- coding: utf-8 -*-
"""Create the GitHub release for v2.0.0 and upload the portable archive."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

TOKEN = os.environ["GH_TOKEN_LOCAL"]
API = "https://api.github.com/repos/omaryounesEG/easy-record-meeting"
HERE = r"H:/Meeting_REC"
ZIP = os.path.join(HERE, "dist", "EasyRecordMeeting-2.0.0-win64.zip")
NOTES = os.path.join(HERE, "docs", "RELEASE_NOTES_v2.0.0.md")


def call(url: str, method: str = "GET", data: bytes | None = None,
         content_type: str = "application/json"):
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "easyrec-release")
    if data is not None:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=900) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = {"message": raw[:200].decode("utf-8", "replace")}
        return exc.code, payload


def main() -> None:
    sha = open(os.path.join(HERE, "dist", "SHA256.txt"), encoding="utf-8").read().split()[0]
    body = open(NOTES, encoding="utf-8").read()
    body = body.replace("**SHA-256** of the attached archive is listed in the release body below.",
                        f"**SHA-256:** `{sha}`")
    body += (f"\n\n### Assets\n\n- `EasyRecordMeeting-2.0.0-win64.zip` — "
             f"OMAR_REC.exe + ffmpeg.exe + docs ({round(os.path.getsize(ZIP) / 1048576, 1)} MB)\n"
             f"- SHA-256: `{sha}`\n")

    # reuse the release if it already exists
    status, existing = call(f"{API}/releases/tags/v2.0.0")
    if status == 200:
        rel = existing
        print("release already exists:", rel["html_url"])
    else:
        payload = json.dumps({
            "tag_name": "v2.0.0",
            "name": "Easy Record Meeting 2.0.0 — مسجّل الاجتماعات الذكي",
            "body": body,
            "draft": False,
            "prerelease": False,
        }).encode("utf-8")
        status, rel = call(f"{API}/releases", "POST", payload)
        print("created:", status, rel.get("html_url") or rel.get("message"))

    upload_url = rel["upload_url"].split("{")[0]
    for asset in rel.get("assets", []):
        if asset["name"] == os.path.basename(ZIP):
            print("asset already uploaded:", asset["size"], "bytes")
            print("RELEASE_URL", rel["html_url"])
            return

    print("uploading", round(os.path.getsize(ZIP) / 1048576, 1), "MB ...")
    with open(ZIP, "rb") as fh:
        blob = fh.read()
    url = f"{upload_url}?name=EasyRecordMeeting-2.0.0-win64.zip"
    status, asset = call(url, "POST", blob, "application/zip")
    print("upload:", status, asset.get("name"), asset.get("size"), "bytes",
          asset.get("message", ""))
    print("RELEASE_URL", rel["html_url"])


if __name__ == "__main__":
    main()
