#!/usr/bin/env python3
"""PreToolUse reminder: unknown-path search belongs in a child, not the parent.

Does not block. Fail-open. Named-file grep stays silent.
"""

from __future__ import annotations

import json
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
SEARCH_TOOLS = GREP_TOOLS | LIST_TOOLS

NAG = (
    "Unknown-path search belongs in spawn_subagent so the parent window does "
    "not fill toward compact. On Grok Build, omit subagent_type (cloud "
    "general-purpose) or use feature-dev:code-explorer with no model. Do not "
    "pin plugin explorers to ollama-gemma4: that model entry is a 16K window "
    "and plugin explore inject is ~24K, so the child overflows before tools. "
    "Named-file grep on the parent is fine."
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


def _wide_roots() -> set[Path]:
    home = Path.home()
    return {home, home / ".grok", home / ".claude", home / "repos", Path("/")}


def is_wide_search(tool: str, tool_input: dict[str, Any]) -> bool:
    if tool not in SEARCH_TOOLS:
        return False
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
        return tool in GREP_TOOLS
    try:
        resolved = Path(path).expanduser().resolve()
    except OSError:
        resolved = Path(path).expanduser()
    if resolved.is_file():
        return False
    return resolved in _wide_roots()


def decide(event: dict[str, Any]) -> dict[str, Any] | None:
    tool = _tool_name(event)
    if not is_wide_search(tool, _tool_input(event)):
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": NAG,
        }
    }


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
