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


def _allow(tool: str, tool_input: dict, session_id: str | None = None) -> None:
    event: dict = {"tool_name": tool, "tool_input": tool_input}
    if session_id is not None:
        event["session_id"] = session_id
    result = SEARCH.decide(event)
    if result is not None:
        raise AssertionError(f"expected allow, got deny: {result}")


def _deny(tool: str, tool_input: dict, session_id: str | None = None) -> dict:
    event: dict = {"tool_name": tool, "tool_input": tool_input}
    if session_id is not None:
        event["session_id"] = session_id
    result = SEARCH.decide(event)
    assert result is not None
    return result


class PreferSpawnSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self._state = tempfile.TemporaryDirectory()
        self._old_state = os.environ.get("PREFER_SPAWN_SEARCH_STATE_DIR")
        self._old_max = os.environ.get("SUBAGENTS_FIRST_PARENT_SEARCH_MAX")
        self._old_window = os.environ.get("SUBAGENTS_FIRST_PARENT_SEARCH_WINDOW_SEC")
        os.environ["PREFER_SPAWN_SEARCH_STATE_DIR"] = self._state.name
        os.environ["SUBAGENTS_FIRST_PARENT_SEARCH_MAX"] = "3"
        os.environ["SUBAGENTS_FIRST_PARENT_SEARCH_WINDOW_SEC"] = "600"

    def tearDown(self) -> None:
        if self._old_state is None:
            os.environ.pop("PREFER_SPAWN_SEARCH_STATE_DIR", None)
        else:
            os.environ["PREFER_SPAWN_SEARCH_STATE_DIR"] = self._old_state
        if self._old_max is None:
            os.environ.pop("SUBAGENTS_FIRST_PARENT_SEARCH_MAX", None)
        else:
            os.environ["SUBAGENTS_FIRST_PARENT_SEARCH_MAX"] = self._old_max
        if self._old_window is None:
            os.environ.pop("SUBAGENTS_FIRST_PARENT_SEARCH_WINDOW_SEC", None)
        else:
            os.environ["SUBAGENTS_FIRST_PARENT_SEARCH_WINDOW_SEC"] = self._old_window
        self._state.cleanup()

    def test_named_file_is_allowed(self) -> None:
        path = Path(__file__).resolve()
        _allow("grep", {"path": str(path), "pattern": "x"})

    def test_missing_path_grep_is_allowed(self) -> None:
        _allow("grep", {"pattern": "x"})

    def test_home_dir_single_grep_is_allowed(self) -> None:
        _allow("grep", {"path": str(Path.home()), "pattern": "x"})

    def test_globstar_single_is_allowed(self) -> None:
        _allow("Glob", {"glob": "**/*.md"})

    def test_directory_grep_is_allowed(self) -> None:
        _allow("grep", {"path": str(HOOKS), "pattern": "x"})

    def test_repos_dir_single_grep_is_allowed(self) -> None:
        repos = Path.home() / "repos"
        if not repos.is_dir():
            self.skipTest("~/repos is not a directory")
        _allow("grep", {"path": str(repos), "pattern": "x"})

    def test_list_dir_of_hooks_is_allowed(self) -> None:
        _allow("list_dir", {"target_directory": str(HOOKS)})

    def test_list_dir_home_is_allowed(self) -> None:
        _allow("list_dir", {"target_directory": str(Path.home())})

    def test_shell_rg_cwd_is_allowed(self) -> None:
        _allow("run_terminal_command", {"command": "rg prefer-spawn-search"})

    def test_unpiped_grep_cwd_is_allowed(self) -> None:
        _allow("run_terminal_command", {"command": "grep foo"})

    def test_and_single_grep_is_allowed(self) -> None:
        _allow("run_terminal_command", {"command": "true && grep foo"})

    def test_rg_piped_to_head_is_allowed(self) -> None:
        _allow(
            "run_terminal_command",
            {"command": "rg prefer-spawn-search | head"},
        )

    def test_piped_ss_grep_is_allowed(self) -> None:
        _allow("run_terminal_command", {"command": "ss -tnp | grep 11434"})

    def test_piped_git_show_grep_is_allowed(self) -> None:
        _allow(
            "run_terminal_command",
            {"command": "git show HEAD:toolkit.yaml | grep version"},
        )

    def test_piped_journalctl_rg_is_allowed(self) -> None:
        _allow("run_terminal_command", {"command": "journalctl -u x | rg error"})

    def test_piped_stderr_grep_is_allowed(self) -> None:
        _allow("run_terminal_command", {"command": "ss -tnp |& grep 11434"})

    def test_double_piped_grep_is_allowed(self) -> None:
        _allow(
            "run_terminal_command",
            {"command": "ss -tnp | grep 11434 | grep LISTEN"},
        )

    def test_piped_grep_forest_path_is_allowed(self) -> None:
        _allow(
            "run_terminal_command",
            {"command": f"ss -tnp | grep foo {Path.home()}"},
        )

    def test_shell_rg_named_file_is_allowed(self) -> None:
        path = Path(__file__).resolve()
        _allow("Bash", {"command": f"rg prefer-spawn-search {path}"})

    def test_shell_rg_one_dir_is_allowed(self) -> None:
        _allow("Bash", {"command": f"rg prefer-spawn-search {HOOKS}"})

    def test_shell_rg_two_dirs_is_allowed(self) -> None:
        other = HOOKS.parent
        _allow("Bash", {"command": f"rg prefer-spawn-search {HOOKS} {other}"})

    def test_find_one_dir_is_allowed(self) -> None:
        _allow("run_terminal_command", {"command": f"find {HOOKS}"})

    def test_find_home_is_allowed(self) -> None:
        _allow("run_terminal_command", {"command": f"find {Path.home()}"})

    def test_shell_git_status_is_allowed(self) -> None:
        _allow("run_terminal_command", {"command": "git status -sb"})

    def test_compound_two_rg_is_denied(self) -> None:
        result = _deny(
            "run_terminal_command",
            {"command": f"rg a {HOOKS} && rg b {HOOKS.parent}"},
        )
        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")
        reason = result["reason"]
        self.assertIn("SPAWN a child", reason)
        self.assertIn("discovery loop", reason.lower())
        self.assertIn("One search command", reason)

    def test_compound_rg_semicolon_is_denied(self) -> None:
        _deny(
            "run_terminal_command",
            {"command": f"rg a {HOOKS}; rg b {HOOKS.parent}"},
        )

    def test_same_tree_repeated_is_allowed(self) -> None:
        for _ in range(5):
            _allow(
                "grep",
                {"path": str(HOOKS), "pattern": "x"},
                session_id="same-tree",
            )

    def test_fourth_distinct_tree_is_denied(self) -> None:
        trees = []
        for i in range(4):
            tree = Path(self._state.name) / f"tree{i}"
            tree.mkdir()
            trees.append(tree)
        for tree in trees[:3]:
            _allow(
                "grep",
                {"path": str(tree), "pattern": "x"},
                session_id="loop1",
            )
        result = _deny(
            "grep",
            {"path": str(trees[3]), "pattern": "x"},
            session_id="loop1",
        )
        self.assertIn("SPAWN a child", result["reason"])

    def test_named_file_does_not_count_toward_streak(self) -> None:
        path = Path(__file__).resolve()
        trees = []
        for i in range(3):
            tree = Path(self._state.name) / f"n{i}"
            tree.mkdir()
            trees.append(tree)
        for tree in trees:
            _allow(
                "grep",
                {"path": str(tree), "pattern": "x"},
                session_id="files-skip",
            )
            _allow(
                "grep",
                {"path": str(path), "pattern": "x"},
                session_id="files-skip",
            )

    def test_escape_hatch_allows_compound_search(self) -> None:
        old = os.environ.get("SUBAGENTS_FIRST_ALLOW_PARENT_SEARCH")
        os.environ["SUBAGENTS_FIRST_ALLOW_PARENT_SEARCH"] = "1"
        try:
            _allow(
                "run_terminal_command",
                {"command": f"rg a {HOOKS} && rg b {HOOKS.parent}"},
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
