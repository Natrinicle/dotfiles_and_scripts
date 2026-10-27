#!/usr/bin/env python3
"""PreToolUse gate for spawn_subagent / Task.

Grok ``[subagents.models]`` matches the exact ``subagent_type``. Plugin types
such as ``feature-dev:code-explorer`` miss a ``code-explorer`` pin and inherit
the parent cloud model. When an explore-class spawn omits ``model``, this hook
sets it to the suffix pin (or the ``explore`` pin / ``ollama-gemma4``) and
tells the parent via ``additionalContext``.

Explicit cloud ``model`` is left in place. Reviewers and ``general-purpose``
are untouched. Any error fails open (exit 0, no rewrite).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_LOCAL = "ollama-gemma4"
GROK_SPAWN_TOOLS = frozenset({"spawn_subagent"})
CLAUDE_SPAWN_TOOLS = frozenset({"Task", "Agent"})
EXPLORE_CLASS = frozenset(
    {
        "explore",
        "code-explorer",
        "conversation-analyzer",
        "plugin-validator",
        "local-extract",
        "local-search",
    }
)
LOCAL_PREFIXES = ("ollama-", "litellm-")
LOCAL_ALIASES = frozenset(
    {
        "gemma4",
        "local-gemma",
        "local-fast",
        "local-coder",
        "ollama",
    }
)
USAGE_LOG = Path(
    os.environ.get(
        "SPAWN_PIN_USAGE_LOG",
        str(Path.home() / ".firecrawl" / "model-routing" / "usage-log.jsonl"),
    )
)
FAIL_OPEN = (
    OSError,
    TypeError,
    ValueError,
    KeyError,
    AttributeError,
    json.JSONDecodeError,
)


def _first(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return default


def _load_event() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    payload = json.loads(raw)
    return payload if isinstance(payload, dict) else {}


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


def _is_local_model(model: str) -> bool:
    text = model.strip().lower()
    if not text:
        return False
    if text.startswith(LOCAL_PREFIXES):
        return True
    return text in LOCAL_ALIASES


def _type_suffix(subagent_type: str) -> str:
    if ":" in subagent_type:
        return subagent_type.rsplit(":", 1)[-1]
    return subagent_type


def _is_explore_class(subagent_type: str) -> bool:
    name = subagent_type.strip()
    if not name:
        return False
    return name in EXPLORE_CLASS or _type_suffix(name) in EXPLORE_CLASS


def _read_toml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        import tomllib
    except ImportError:
        return {}
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _pin_tables() -> tuple[dict[str, str], dict[str, str]]:
    grok_home = Path.home() / ".grok"
    env_home = os.environ.get("GROK_HOME")
    if env_home:
        grok_home = Path(env_home)
    data = _read_toml(grok_home / "config.toml")
    subagents = data.get("subagents")
    if not isinstance(subagents, dict):
        return {}, {}
    models_raw = subagents.get("models")
    models: dict[str, str] = {}
    if isinstance(models_raw, dict):
        for key, value in models_raw.items():
            if isinstance(key, str) and isinstance(value, str) and value.strip():
                models[key] = value.strip()
    roles_raw = subagents.get("roles")
    roles: dict[str, str] = {}
    if isinstance(roles_raw, dict):
        for key, body in roles_raw.items():
            if not isinstance(key, str) or not isinstance(body, dict):
                continue
            model = body.get("model")
            if isinstance(model, str) and model.strip():
                roles[key] = model.strip()
    return models, roles


def _lookup_pin(
    subagent_type: str, models: dict[str, str], roles: dict[str, str]
) -> tuple[str | None, str | None]:
    """Return (exact_pin, suffix_or_role_pin)."""
    exact = models.get(subagent_type)
    suffix = _type_suffix(subagent_type)
    fallback = models.get(suffix) if suffix != subagent_type else None
    if fallback is None:
        fallback = roles.get(subagent_type) or roles.get(suffix)
    return exact, fallback


def _default_local(models: dict[str, str]) -> str:
    for key in ("explore", "code-explorer", "local-extract"):
        pinned = models.get(key)
        if pinned and _is_local_model(pinned):
            return pinned
    return DEFAULT_LOCAL


def _emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    sys.stdout.write("\n")


def _log(record: dict[str, Any]) -> None:
    try:
        USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        with USAGE_LOG.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        return


def _context_rewrite(subagent_type: str, local_model: str, pin_source: str) -> str:
    quoted = subagent_type if ":" not in subagent_type else f'"{subagent_type}"'
    return (
        f"Explore-class subagent {subagent_type} has no exact [subagents.models] "
        f"pin ({pin_source}), so this spawn's model was set to {local_model}. "
        f'Prefer type explore (already pinned) or add {quoted} = "{local_model}" '
        "under [subagents.models]. Explicit cloud model is left unchanged."
    )


def _context_cloud(subagent_type: str, model: str) -> str:
    return (
        f"Explore-class subagent {subagent_type} passed model {model} with no "
        "exact local pin. That cloud model will run. Omit model and use type "
        "explore, or pin this type to ollama-gemma4."
    )


def _context_claude(subagent_type: str) -> str:
    return (
        f"Explore-class Task {subagent_type}: set the Agent model from the "
        "model-routing-table memory file (T0/T1). Grok [subagents.models] pins "
        "do not apply on Claude Code."
    )


def decide(event: dict[str, Any]) -> dict[str, Any] | None:
    tool = _tool_name(event)
    if tool not in GROK_SPAWN_TOOLS and tool not in CLAUDE_SPAWN_TOOLS:
        return None
    tool_input = _tool_input(event)
    subagent_type = str(
        _first(tool_input, "subagent_type", "subagentType", default="") or ""
    ).strip()
    if not _is_explore_class(subagent_type):
        return None
    raw_model = _first(tool_input, "model", default="")
    model = str(raw_model).strip() if raw_model is not None else ""
    models, roles = _pin_tables()
    exact_pin, fallback_pin = _lookup_pin(subagent_type, models, roles)

    if tool in CLAUDE_SPAWN_TOOLS:
        if model:
            return None
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": _context_claude(subagent_type),
            }
        }

    if exact_pin and _is_local_model(exact_pin) and not model:
        return None
    if model and _is_local_model(model):
        return None

    if model:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": _context_cloud(subagent_type, model),
            }
        }

    local_model = (
        fallback_pin if fallback_pin and _is_local_model(fallback_pin) else None
    )
    pin_source = "suffix/role pin" if local_model else "default T0"
    if local_model is None:
        local_model = _default_local(models)
    updated = dict(tool_input)
    updated["model"] = local_model
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "updatedInput": updated,
            "additionalContext": _context_rewrite(
                subagent_type, local_model, pin_source
            ),
        }
    }


def main() -> int:
    try:
        event = _load_event()
        result = decide(event)
    except FAIL_OPEN:
        return 0
    if not result:
        return 0
    try:
        _emit(result)
        output = result.get("hookSpecificOutput") or {}
        updated = output.get("updatedInput") or {}
        tool_input = _tool_input(event)
        _log(
            {
                "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "task_id": "spawn-subagent-local-pin",
                "skill": "spawn-subagent-local-pin",
                "subagent_type": str(
                    _first(tool_input, "subagent_type", "subagentType", default="")
                ),
                "model": updated.get("model")
                or _first(tool_input, "model", default=""),
                "action": "rewrite" if "updatedInput" in output else "warn",
                "escalated": False,
                "validation": "hook",
            }
        )
    except FAIL_OPEN:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
