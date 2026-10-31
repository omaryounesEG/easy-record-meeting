# -*- coding: utf-8 -*-
"""Updater tests (offline-safe: the network call is monkeypatched)."""

from __future__ import annotations

import io
import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from easyrec import updater


class TestVersionMath(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(updater.parse_version("v2.1.0"), (2, 1, 0))
        self.assertEqual(updater.parse_version("2.0"), (2, 0))
        self.assertEqual(updater.parse_version("2.0.0-beta.3"), (2, 0, 0))
        self.assertEqual(updater.parse_version(""), (0,))

    def test_is_newer(self):
        self.assertTrue(updater.is_newer("v2.0.1", "v2.0.0"))
        self.assertTrue(updater.is_newer("3.0", "2.9.9"))
        self.assertFalse(updater.is_newer("v2.0.0", "v2.0.0"))
        self.assertFalse(updater.is_newer("v1.9.9", "v2.0.0"))
        self.assertTrue(updater.is_newer("v2.1", "v2.0.9"))


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def _payload(tag="v9.9.9"):
    return _FakeResponse(json.dumps({
        "tag_name": tag,
        "html_url": f"https://github.com/o/r/releases/tag/{tag}",
        "body": "Release notes",
        "published_at": "2026-10-31T00:00:00Z",
    }).encode())


class TestFetch(unittest.TestCase):
    def test_available(self):
        with mock.patch("urllib.request.urlopen", return_value=_payload("v9.9.9")):
            info = updater.fetch_latest("owner/repo", "v2.0.0")
        self.assertTrue(info.ok)
        self.assertEqual(info.latest, "v9.9.9")
        self.assertTrue(info.newer)

    def test_same_version(self):
        with mock.patch("urllib.request.urlopen", return_value=_payload("v2.0.0")):
            info = updater.fetch_latest("owner/repo", "v2.0.0")
        self.assertFalse(info.newer)

    def test_404_is_reported_not_raised(self):
        error = updater.urllib.error.HTTPError("url", 404, "Not Found", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=error):
            info = updater.fetch_latest("owner/repo", "v2.0.0")
        self.assertFalse(info.ok)
        self.assertIn("404", info.error)

    def test_offline_is_reported_not_raised(self):
        with mock.patch("urllib.request.urlopen", side_effect=OSError("no network")):
            info = updater.fetch_latest("owner/repo", "v2.0.0")
        self.assertFalse(info.ok)
        self.assertIn("no network", info.error)

    def test_rate_limit(self):
        error = updater.urllib.error.HTTPError("url", 403, "Forbidden", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=error):
            info = updater.fetch_latest("owner/repo", "v2.0.0")
        self.assertIn("rate limit", info.error or "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
