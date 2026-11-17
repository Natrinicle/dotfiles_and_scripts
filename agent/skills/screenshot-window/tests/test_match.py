#!/usr/bin/env python3
"""Unit tests for title matching and /tmp cleanup guards (no KWin)."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "scripts" / "screenshot-window.py"


def _load():
    spec = importlib.util.spec_from_file_location("screenshot_window", SRC)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SRC}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["screenshot_window"] = mod
    spec.loader.exec_module(mod)
    return mod


class MatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load()
        cls.rows = [
            {
                "uuid": "{aaa}",
                "caption": "Wallpaper — System Settings",
                "resourceClass": "systemsettings",
                "resourceName": "systemsettings",
            },
            {
                "uuid": "{bbb}",
                "caption": "Breezy Weather animated KDE live wallpaper — grok",
                "resourceClass": "terminology",
                "resourceName": "main",
            },
        ]

    def test_unique_title(self) -> None:
        hits = self.mod.match_windows(
            self.rows,
            uuid=None,
            title="Wallpaper — System Settings",
            resource_class=None,
        )
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["uuid"], "{aaa}")

    def test_ambiguous_breezy(self) -> None:
        extra = dict(self.rows[0])
        extra["uuid"] = "{ccc}"
        extra["caption"] = "Breezy Weather Preview"
        hits = self.mod.match_windows(
            [*self.rows, extra], uuid=None, title="Breezy Weather", resource_class=None
        )
        self.assertEqual(len(hits), 2)

    def test_uuid_braces(self) -> None:
        hits = self.mod.match_windows(
            self.rows, uuid="aaa", title=None, resource_class=None
        )
        self.assertEqual(len(hits), 1)

    def test_slug(self) -> None:
        self.assertEqual(
            self.mod._slug("Wallpaper — System Settings"), "wallpaper-system-settings"
        )

    def test_tmpish(self) -> None:
        self.assertTrue(self.mod._is_tmpish(Path("/tmp/agent-screenshots/a.png")))
        self.assertFalse(
            self.mod._is_tmpish(Path.home() / "Pictures" / "Screenshots" / "a.png")
        )

    def test_cleanup_refuses_home(self) -> None:
        dest = Path.home() / ".cache" / "screenshot-window-test-refuse"
        dest.mkdir(parents=True, exist_ok=True)
        p = dest / "nope.png"
        p.write_bytes(b"x")
        try:
            ns = type(
                "Args",
                (),
                {"path": str(p), "force": False, "dir": None, "rmdir": False},
            )()
            with self.assertRaises(SystemExit):
                self.mod.cmd_cleanup(ns)
            self.assertTrue(p.is_file())
        finally:
            p.unlink(missing_ok=True)
            try:
                dest.rmdir()
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
