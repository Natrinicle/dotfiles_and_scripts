#!/usr/bin/env python3
"""PreToolUse gate: forest and multi-location search belongs in a child.

Allows a single rg/grep/find/list of one tree (including a git repo root)
and a grep-family filter of stdin (`ss | grep 11434`).
Denies $HOME, /, ~/repos, missing-path workspace hunt, two+ directory
operands, and unpiped rg/grep with no path. Fail-open on parse errors.
Escape: SUBAGENTS_FIRST_ALLOW_PARENT_SEARCH=1.
"""

from __future__ import annotations

import json
import os
import shlex
import sys
from pathlib import Path
from typing import Any

FAIL_OPEN = (
    OSError,
    TypeError,
    ValueError,
    KeyError,
    AttributeError,
    json.JSONDecodeError,
)

GREP_TOOLS = frozenset({"grep", "Grep", "grep_search", "codebase_search"})
LIST_TOOLS = frozenset({"list_dir", "LS", "Glob", "glob"})
SHELL_TOOLS = frozenset({"Bash", "bash", "run_terminal_command", "shell"})
SEARCH_TOOLS = GREP_TOOLS | LIST_TOOLS | SHELL_TOOLS
SEARCH_BINS = frozenset(
    {"rg", "ripgrep", "grep", "egrep", "fgrep", "ag", "ack", "find"}
)
GREP_BINS = SEARCH_BINS - {"find"}
SEP = frozenset({"|", "||", "&&", ";", "&", "|&"})
PIPE = frozenset({"|", "|&"})
FLAGS_WITH_ARG = frozenset(
    {
        "-e",
        "-f",
        "-g",
        "-C",
        "-A",
        "-B",
        "-m",
        "-d",
        "--glob",
        "--iglob",
        "--max-count",
        "--max-depth",
        "--regexp",
        "--file",
        "--path",
        "--type",
        "-t",
        "-j",
    }
)

BLOCK_REASON = (
    "Parent forest or multi-location search is blocked (rule subagents-first, "
    "hook prefer-spawn-search). A single rg/grep/find/list of one tree belongs "
    "on the parent: spawn tax plus re-ingest exceeds running the command. "
    "A single command piped into grep (ss | grep 11434) also stays here.\n"
    "Spawn when:\n"
    "- Searching several locations ($HOME, ~/repos, two+ trees)\n"
    "- Installing software including config and service files\n"
    "- Large extract, decompile, or multi-file implementation\n"
    "Several independent units → skill agent-graphs (workflow agent-graph). "
    "Inner retry is loop-until-green. Bug hunt stays find-patch-loop.\n"
    "More than a single command: prefer a helper script "
    "(rule prefer-helper-scripts). One-shot verify (did this open the port) "
    "stays on the parent. Reusable multi-grep diagnostics "
    "(router iptables/clients/stats) should be a helper.\n"
    "Escape hatch: SUBAGENTS_FIRST_ALLOW_PARENT_SEARCH=1."
)


def _first(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return default


def _tool_name(event: dict[str, Any]) -> str:
    return str(_first(event, "tool_name", "toolName", default="") or "")


def _tool_input(event: dict[str, Any]) -> dict[str, Any]:
    value = _first(event, "tool_input", "toolInput", default={})
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {}
    return value if isinstance(value, dict) else {}


def _allow_parent_search() -> bool:
    return os.environ.get(
        "SUBAGENTS_FIRST_ALLOW_PARENT_SEARCH", ""
    ).strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _forest_roots() -> set[Path]:
    home = Path.home()
    return {home, home / "repos", Path("/")}


def _resolve(path: str) -> Path:
    try:
        return Path(path).expanduser().resolve()
    except OSError:
        return Path(path).expanduser()


def _is_file(path: str) -> bool:
    try:
        return _resolve(path).is_file()
    except OSError:
        return False


def _is_wide_dir(path: str) -> bool:
    raw = path.strip()
    if raw in {"", ".", "..", "~", "/"}:
        return True
    return _resolve(raw) in _forest_roots()


def _deny_payload() -> dict[str, Any]:
    return {
        "decision": "block",
        "reason": BLOCK_REASON,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": BLOCK_REASON,
        },
    }


def _segments_with_seps(tokens: list[str]) -> list[tuple[str | None, list[str]]]:
    """Yield (separator_before, segment). First segment has separator None.

    Only `|` and `|&` count as pipes. `||`, `&&`, `;`, and `&` are not pipes.
    shlex splits on spaces, so glued `file|grep` is a known parse limit.
    """
    segs: list[tuple[str | None, list[str]]] = []
    cur: list[str] = []
    sep_before: str | None = None
    for token in tokens:
        if token in SEP:
            if cur:
                segs.append((sep_before, cur))
                cur = []
            sep_before = token
        else:
            cur.append(token)
    if cur:
        segs.append((sep_before, cur))
    return segs


def _segments(tokens: list[str]) -> list[list[str]]:
    return [seg for _, seg in _segments_with_seps(tokens)]


def _skip_env_and_wrappers(seg: list[str]) -> list[str]:
    i = 0
    while i < len(seg) and "=" in seg[i] and not seg[i].startswith("-"):
        i += 1
    wrappers = {"command", "time", "env", "nice", "nohup"}
    while i < len(seg) and Path(seg[i]).name in wrappers:
        i += 1
        while i < len(seg) and seg[i].startswith("-"):
            i += 1
    return seg[i:]


def _positionals(seg: list[str]) -> list[str]:
    out: list[str] = []
    skip_next = False
    for token in seg[1:]:
        if skip_next:
            skip_next = False
            continue
        if token.startswith("-") and token != "-":
            name = token.split("=", 1)[0]
            takes_arg = name in FLAGS_WITH_ARG or (
                len(name) == 2 and name[1] in "efgCABMdtj"
            )
            if takes_arg and "=" not in token:
                skip_next = True
            continue
        out.append(token)
    return out


def is_wide_shell(command: str) -> bool:
    if not command.strip():
        return False
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        lowered = command.lower()
        return any(
            f" {name} " in f" {lowered} " or lowered.startswith(f"{name} ")
            for name in SEARCH_BINS
        )
    for sep_before, seg in _segments_with_seps(tokens):
        body = _skip_env_and_wrappers(seg)
        if not body:
            continue
        binary = Path(body[0]).name
        if binary == "git" and len(body) > 1 and body[1] == "grep":
            binary = "grep"
            body = body[1:]
        if binary not in SEARCH_BINS:
            continue
        positionals = _positionals(body)
        if binary == "find":
            start = positionals[0] if positionals else "."
            if _is_wide_dir(start):
                return True
            continue
        paths = positionals[1:]
        if not paths:
            if binary in GREP_BINS and sep_before in PIPE:
                continue
            return True
        if any(_is_wide_dir(path) for path in paths):
            return True
        dir_paths = [path for path in paths if not _is_file(path)]
        if len(dir_paths) > 1:
            return True
    return False


def is_wide_search(tool: str, tool_input: dict[str, Any]) -> bool:
    if tool not in SEARCH_TOOLS:
        return False
    if tool in SHELL_TOOLS:
        command = str(_first(tool_input, "command", "cmd", default="") or "")
        return is_wide_shell(command)
    glob = str(_first(tool_input, "glob", default="") or "")
    path = str(
        _first(
            tool_input,
            "path",
            "target_directory",
            "target_file",
            default="",
        )
        or ""
    ).strip()
    if "**" in glob and (not path or _is_wide_dir(path)):
        return True
    if not path:
        return tool in GREP_TOOLS or tool in {"Glob", "glob"}
    if _is_file(path):
        return False
    return _is_wide_dir(path)


def decide(event: dict[str, Any]) -> dict[str, Any] | None:
    if _allow_parent_search():
        return None
    if not is_wide_search(_tool_name(event), _tool_input(event)):
        return None
    return _deny_payload()


def main() -> int:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
        if not isinstance(event, dict):
            return 0
        result = decide(event)
    except FAIL_OPEN:
        return 0
    if result:
        sys.stdout.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
