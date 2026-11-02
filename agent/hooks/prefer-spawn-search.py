#!/usr/bin/env python3
"""PreToolUse gate: unknown-path search belongs in a child, not the parent.

Denies wide grep/list/rg on the parent. Named-file grep stays allowed.
Fail-open on parse errors. Escape: SUBAGENTS_FIRST_ALLOW_PARENT_SEARCH=1.
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
SEP = frozenset({"|", "||", "&&", ";", "&"})
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
    "Parent unknown-path search is blocked (rule subagents-first, hook "
    "prefer-spawn-search). Do not grep, list, or rg the tree here.\n"
    "Pick a shape, then run it:\n"
    "- One child-capable unit (one search, one extract, one implementation "
    "slice) → spawn_subagent. On Grok Build omit subagent_type (cloud "
    "general-purpose). Do not pin plugin explorers to ollama-gemma4.\n"
    "- Several units that do not consume each other's output, or a gate / "
    "named output between steps → skill agent-graphs (workflow agent-graph). "
    "Inner retry is loop-until-green. Bug hunt stays find-patch-loop.\n"
    "- User named 1–2 exact files → retry this tool with those file paths.\n"
    "Parent keeps: ask the user, land commit/push/server, synthesize, verify. "
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


def _wide_roots() -> set[Path]:
    home = Path.home()
    return {home, home / ".grok", home / ".claude", home / "repos", Path("/")}


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


def _is_git_toplevel(resolved: Path) -> bool:
    return (resolved / ".git").exists()


def _is_wide_dir(path: str) -> bool:
    raw = path.strip()
    if raw in {"", ".", "..", "~", "/"}:
        return True
    resolved = _resolve(raw)
    if resolved in _wide_roots():
        return True
    if resolved.is_file():
        return False
    return bool(resolved.is_dir() and _is_git_toplevel(resolved))


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


def _segments(tokens: list[str]) -> list[list[str]]:
    segs: list[list[str]] = []
    cur: list[str] = []
    for token in tokens:
        if token in SEP:
            if cur:
                segs.append(cur)
                cur = []
        else:
            cur.append(token)
    if cur:
        segs.append(cur)
    return segs


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
    for seg in _segments(tokens):
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
            if _is_wide_dir(start) or not _is_file(start):
                return True
            continue
        paths = positionals[1:]
        if not paths:
            return True
        if any(not _is_file(path) for path in paths):
            return True
    return False


def is_wide_search(tool: str, tool_input: dict[str, Any]) -> bool:
    if tool not in SEARCH_TOOLS:
        return False
    if tool in SHELL_TOOLS:
        command = str(_first(tool_input, "command", "cmd", default="") or "")
        return is_wide_shell(command)
    glob = str(_first(tool_input, "glob", default="") or "")
    if "**" in glob:
        return True
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
    if not path:
        return tool in GREP_TOOLS or tool in {"Glob", "glob"}
    if _is_file(path):
        return False
    if tool in LIST_TOOLS:
        return _is_wide_dir(path)
    return True


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
