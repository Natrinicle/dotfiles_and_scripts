#!/usr/bin/env python3
"""PreToolUse gate: nested discovery loops belong in a child.

A single search command stays on the parent, including $HOME, /, ~/repos,
two directory operands, cwd rg, and rg piped to head. Spawn tax plus
re-ingest exceeds that one command.

Denies a discovery loop: two+ tree-search invocations in one command, or
a fourth distinct tree in the session window (default 3 / 10 minutes).
Named-file grep and stdin grep (ss | grep) never count. Fail-open on
parse errors. Escape: SUBAGENTS_FIRST_ALLOW_PARENT_SEARCH=1.
"""

from __future__ import annotations

import json
import os
import shlex
import sys
import time
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
# Longer first so `||` / `&&` / `|&` are not split into `|` / `&`.
GLUED_SEPS = ("||", "&&", "|&", "|", ";", "&")
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
    "Nested discovery loop blocked (rule subagents-first, hook "
    "prefer-spawn-search). SPAWN a child (or skill agent-graphs). One "
    "search command stays on the parent, including $HOME / ~/repos / two "
    "dirs / cwd; spawn tax exceeds that one command. This hook fires on "
    "compound search, or a fourth distinct tree in 10 minutes. After a "
    "deny, spawn; do not serial-walk.\n"
    "Escape: SUBAGENTS_FIRST_ALLOW_PARENT_SEARCH=1."
)

DEFAULT_MAX = 3
DEFAULT_WINDOW_SEC = 600


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


def _cwd(event: dict[str, Any], tool_input: dict[str, Any]) -> str:
    raw = _first(tool_input, "cwd", default=None) or _first(
        event, "cwd", "cwd_path", default=""
    )
    text = str(raw or "").strip()
    return text or os.getcwd()


def _session_id(event: dict[str, Any]) -> str:
    return str(
        _first(event, "session_id", "sessionId", "conversation_id", default="") or ""
    ).strip()


def _allow_parent_search() -> bool:
    return os.environ.get(
        "SUBAGENTS_FIRST_ALLOW_PARENT_SEARCH", ""
    ).strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def _parent_search_max() -> int:
    return _int_env("SUBAGENTS_FIRST_PARENT_SEARCH_MAX", DEFAULT_MAX)


def _window_sec() -> int:
    return _int_env("SUBAGENTS_FIRST_PARENT_SEARCH_WINDOW_SEC", DEFAULT_WINDOW_SEC)


def _state_dir() -> Path:
    override = os.environ.get("PREFER_SPAWN_SEARCH_STATE_DIR", "").strip()
    if override:
        return Path(override)
    runtime = os.environ.get("XDG_RUNTIME_DIR", "").strip()
    base = Path(runtime) if runtime else Path(f"/tmp/prefer-spawn-search-{os.getuid()}")
    return base / "prefer-spawn-search"


def _session_key(session_id: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in session_id)
    return cleaned[:128] or "none"


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


def _split_glued_seps(tokens: list[str]) -> list[str]:
    """Split `dir;rg` / `true&&grep` so compound search is still visible."""
    out: list[str] = []
    for token in tokens:
        parts = [token]
        for sep in GLUED_SEPS:
            next_parts: list[str] = []
            for part in parts:
                if part in SEP:
                    next_parts.append(part)
                    continue
                chunks = part.split(sep)
                for i, chunk in enumerate(chunks):
                    if i:
                        next_parts.append(sep)
                    if chunk:
                        next_parts.append(chunk)
            parts = next_parts
        out.extend(parts)
    return out


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


def _shell_search_segments(
    command: str,
) -> list[tuple[str | None, str, list[str]]]:
    """(sep_before, binary, positionals) for search bins in command."""
    if not command.strip():
        return []
    try:
        tokens = _split_glued_seps(shlex.split(command, posix=True))
    except ValueError:
        return []
    out: list[tuple[str | None, str, list[str]]] = []
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
        out.append((sep_before, binary, _positionals(body)))
    return out


def _segment_tree_paths(
    sep_before: str | None,
    binary: str,
    positionals: list[str],
    cwd: str,
) -> list[str] | None:
    """Directory paths this search segment walks, or None if not a tree search."""
    if binary == "find":
        start = positionals[0] if positionals else cwd
        if _is_file(start):
            return None
        return [start]
    paths = positionals[1:]
    if not paths:
        if binary in GREP_BINS and sep_before in PIPE:
            return None
        return [cwd]
    dirs = [path for path in paths if not _is_file(path)]
    if not dirs:
        return None
    return dirs


def tree_invocation_count(command: str, cwd: str) -> int:
    count = 0
    for sep_before, binary, positionals in _shell_search_segments(command):
        if _segment_tree_paths(sep_before, binary, positionals, cwd) is not None:
            count += 1
    return count


def tree_search_paths(
    tool: str, tool_input: dict[str, Any], cwd: str
) -> list[str] | None:
    """Directory paths this tool call searches, or None if not a tree search."""
    if tool not in SEARCH_TOOLS:
        return None
    if tool in SHELL_TOOLS:
        command = str(_first(tool_input, "command", "cmd", default="") or "")
        paths: list[str] = []
        saw = False
        for sep_before, binary, positionals in _shell_search_segments(command):
            segment = _segment_tree_paths(sep_before, binary, positionals, cwd)
            if segment is None:
                continue
            saw = True
            paths.extend(segment)
        if not saw:
            return None
        return paths
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
    if tool in {"Glob", "glob"}:
        return [path or cwd]
    if not path:
        if tool in GREP_TOOLS or glob:
            return [cwd]
        return [cwd]
    if _is_file(path):
        return None
    return [path]


def _normalized_paths(paths: list[str]) -> list[str]:
    return sorted({str(_resolve(path)) for path in paths})


def _load_calls(path: Path, now: float, window: int) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FAIL_OPEN:
        return []
    calls = raw.get("calls") if isinstance(raw, dict) else None
    if not isinstance(calls, list):
        return []
    kept: list[dict[str, Any]] = []
    for call in calls:
        if not isinstance(call, dict):
            continue
        try:
            ts = float(call.get("ts", 0))
        except (TypeError, ValueError):
            continue
        if now - ts > window:
            continue
        stored = call.get("paths")
        if not isinstance(stored, list):
            continue
        kept.append({"ts": ts, "paths": [str(item) for item in stored]})
    return kept


def _save_calls(path: Path, calls: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"calls": calls}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def _streak_should_deny(session_id: str, paths: list[str]) -> bool:
    if not session_id:
        return False
    now = time.time()
    window = _window_sec()
    limit = _parent_search_max()
    state_path = _state_dir() / f"{_session_key(session_id)}.json"
    calls = _load_calls(state_path, now, window)
    normalized = _normalized_paths(paths)
    if calls:
        last = calls[-1].get("paths")
        if (
            isinstance(last, list)
            and _normalized_paths([str(p) for p in last]) == normalized
        ):
            return False
    if len(calls) >= limit:
        return True
    calls.append({"ts": now, "paths": normalized})
    try:
        _save_calls(state_path, calls)
    except FAIL_OPEN:
        return False
    return False


def decide(event: dict[str, Any]) -> dict[str, Any] | None:
    if _allow_parent_search():
        return None
    tool = _tool_name(event)
    if tool not in SEARCH_TOOLS:
        return None
    tool_input = _tool_input(event)
    cwd = _cwd(event, tool_input)
    if tool in SHELL_TOOLS:
        command = str(_first(tool_input, "command", "cmd", default="") or "")
        if tree_invocation_count(command, cwd) >= 2:
            return _deny_payload()
    paths = tree_search_paths(tool, tool_input, cwd)
    if paths is None:
        return None
    if _streak_should_deny(_session_id(event), paths):
        return _deny_payload()
    return None


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
