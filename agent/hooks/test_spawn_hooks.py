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

    def test_directory_grep_is_not_wide(self) -> None:
        self.assertFalse(
            SEARCH.is_wide_search("grep", {"path": str(HOOKS), "pattern": "x"})
        )

    def test_git_toplevel_grep_is_not_wide(self) -> None:
        repo = HOOKS
        while repo != repo.parent and not (repo / ".git").exists():
            repo = repo.parent
        self.assertTrue((repo / ".git").exists())
        self.assertFalse(
            SEARCH.is_wide_search("grep", {"path": str(repo), "pattern": "x"})
        )

    def test_list_dir_git_toplevel_is_not_wide(self) -> None:
        repo = HOOKS
        while repo != repo.parent and not (repo / ".git").exists():
            repo = repo.parent
        self.assertFalse(
            SEARCH.is_wide_search("list_dir", {"target_directory": str(repo)})
        )

    def test_repos_dir_is_wide(self) -> None:
        repos = Path.home() / "repos"
        if not repos.is_dir():
            self.skipTest("~/repos is not a directory")
        self.assertTrue(
            SEARCH.is_wide_search("grep", {"path": str(repos), "pattern": "x"})
        )

    def test_globstar_scoped_to_one_tree_is_not_wide(self) -> None:
        self.assertFalse(
            SEARCH.is_wide_search(
                "Glob", {"glob": "**/*.md", "target_directory": str(HOOKS)}
            )
        )

    def test_list_dir_of_hooks_is_not_wide(self) -> None:
        self.assertFalse(
            SEARCH.is_wide_search("list_dir", {"target_directory": str(HOOKS)})
        )

    def test_list_dir_home_is_wide(self) -> None:
        self.assertTrue(
            SEARCH.is_wide_search("list_dir", {"target_directory": str(Path.home())})
        )

    def test_shell_rg_cwd_is_wide(self) -> None:
        self.assertTrue(
            SEARCH.is_wide_search(
                "run_terminal_command", {"command": "rg prefer-spawn-search"}
            )
        )

    def test_shell_rg_named_file_is_not_wide(self) -> None:
        path = Path(__file__).resolve()
        self.assertFalse(
            SEARCH.is_wide_search("Bash", {"command": f"rg prefer-spawn-search {path}"})
        )

    def test_shell_rg_one_dir_is_not_wide(self) -> None:
        self.assertFalse(
            SEARCH.is_wide_search(
                "Bash", {"command": f"rg prefer-spawn-search {HOOKS}"}
            )
        )

    def test_shell_rg_two_dirs_is_wide(self) -> None:
        other = HOOKS.parent
        self.assertTrue(
            SEARCH.is_wide_search(
                "Bash", {"command": f"rg prefer-spawn-search {HOOKS} {other}"}
            )
        )

    def test_find_one_dir_is_not_wide(self) -> None:
        self.assertFalse(
            SEARCH.is_wide_search("run_terminal_command", {"command": f"find {HOOKS}"})
        )

    def test_find_home_is_wide(self) -> None:
        self.assertTrue(
            SEARCH.is_wide_search(
                "run_terminal_command", {"command": f"find {Path.home()}"}
            )
        )

    def test_shell_git_status_is_not_wide(self) -> None:
        self.assertFalse(
            SEARCH.is_wide_search("run_terminal_command", {"command": "git status -sb"})
        )

    def test_wide_grep_is_denied_not_nagged(self) -> None:
        result = SEARCH.decide({"tool_name": "grep", "tool_input": {"pattern": "x"}})
        assert result is not None
        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")
        reason = result["reason"]
        self.assertIn("spawn tax", reason)
        self.assertIn("agent-graphs", reason)
        self.assertIn("loop-until-green", reason)
        self.assertIn("prefer-helper-scripts", reason)

    def test_named_file_decide_is_none(self) -> None:
        path = Path(__file__).resolve()
        self.assertIsNone(
            SEARCH.decide(
                {"tool_name": "grep", "tool_input": {"path": str(path), "pattern": "x"}}
            )
        )

    def test_escape_hatch_allows_wide_search(self) -> None:
        old = os.environ.get("SUBAGENTS_FIRST_ALLOW_PARENT_SEARCH")
        os.environ["SUBAGENTS_FIRST_ALLOW_PARENT_SEARCH"] = "1"
        try:
            self.assertIsNone(
                SEARCH.decide({"tool_name": "grep", "tool_input": {"pattern": "x"}})
            )
        finally:
            if old is None:
                os.environ.pop("SUBAGENTS_FIRST_ALLOW_PARENT_SEARCH", None)
            else:
                os.environ["SUBAGENTS_FIRST_ALLOW_PARENT_SEARCH"] = old


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
