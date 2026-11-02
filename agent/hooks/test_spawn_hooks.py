#!/usr/bin/env python3
"""Unit tests for spawn-subagent-local-pin, prefer-spawn-search, retarget."""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent


def _load(name: str):
    path = HOOKS / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PIN = _load("spawn-subagent-local-pin.py")
SEARCH = _load("prefer-spawn-search.py")
RETARGET = _load("retarget-grok-plugin-symlinks.py")


class SpawnPinTests(unittest.TestCase):
    def test_plugin_explore_is_not_rewritten_to_local(self) -> None:
        result = PIN.decide(
            {
                "tool_name": "spawn_subagent",
                "tool_input": {"subagent_type": "feature-dev:code-explorer"},
            }
        )
        assert result is not None
        output = result["hookSpecificOutput"]
        self.assertNotIn("updatedInput", output)
        self.assertIn("not pinned to ollama-gemma4", output["additionalContext"])

    def test_native_explore_without_model_is_explore_class(self) -> None:
        self.assertTrue(PIN._is_explore_class("explore"))
        self.assertTrue(PIN._is_explore_class("code-explorer"))
        self.assertFalse(PIN._is_explore_class("feature-dev:code-explorer"))
        self.assertTrue(PIN._is_plugin_explore("feature-dev:code-explorer"))

    def test_general_purpose_untouched(self) -> None:
        self.assertIsNone(
            PIN.decide(
                {
                    "tool_name": "spawn_subagent",
                    "tool_input": {"subagent_type": "general-purpose"},
                }
            )
        )


class PreferSpawnSearchTests(unittest.TestCase):
    def test_named_file_is_silent(self) -> None:
        path = Path(__file__).resolve()
        self.assertFalse(
            SEARCH.is_wide_search("grep", {"path": str(path), "pattern": "x"})
        )

    def test_missing_path_grep_is_wide(self) -> None:
        self.assertTrue(SEARCH.is_wide_search("grep", {"pattern": "x"}))

    def test_home_dir_is_wide(self) -> None:
        self.assertTrue(
            SEARCH.is_wide_search("grep", {"path": str(Path.home()), "pattern": "x"})
        )

    def test_globstar_is_wide(self) -> None:
        self.assertTrue(SEARCH.is_wide_search("Glob", {"glob": "**/*.md"}))


class RetargetTests(unittest.TestCase):
    def test_heals_dangling_unknown_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "cache" / "hookify" / "0.1.1"
            src.mkdir(parents=True)
            (src / "hooks.json").write_text("{}", encoding="utf-8")
            grok = root / "grok-plugins"
            grok.mkdir()
            dangling = grok / "hookify"
            dangling.symlink_to(root / "cache" / "hookify" / "unknown")
            installed = root / "installed_plugins.json"
            installed.write_text(
                json.dumps(
                    {
                        "plugins": {
                            "hookify@claude-plugins-official": [
                                {"installPath": str(src)}
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )
            healed, already, skipped = RETARGET.retarget(grok, installed)
            self.assertEqual(healed, ["hookify"])
            self.assertEqual(already, [])
            self.assertEqual(skipped, [])
            self.assertEqual(os.readlink(dangling), str(src))
            self.assertTrue((grok / ".synced-from-claude.txt").is_file())

    def test_skips_when_already_correct(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "cache" / "hookify" / "0.1.1"
            src.mkdir(parents=True)
            grok = root / "grok-plugins"
            grok.mkdir()
            dest = grok / "hookify"
            dest.symlink_to(src)
            installed = root / "installed_plugins.json"
            installed.write_text(
                json.dumps(
                    {
                        "plugins": {
                            "hookify@claude-plugins-official": [
                                {"installPath": str(src)}
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )
            healed, already, skipped = RETARGET.retarget(grok, installed)
            self.assertEqual(healed, [])
            self.assertEqual(already, ["hookify"])
            self.assertEqual(skipped, [])


if __name__ == "__main__":
    unittest.main()
