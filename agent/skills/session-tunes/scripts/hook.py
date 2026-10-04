#!/usr/bin/env python3
"""Fast hook: map Grok/Claude lifecycle events to the session-tunes state file.

Prints nothing on stdout so UserPromptSubmit/Stop cannot block the turn.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from state import load_state, update_session

EVENT_STATE = {
    "UserPromptSubmit": "busy",
    "user_prompt_submit": "busy",
    "Stop": "idle",
    "stop": "idle",
    "StopCancelled": "idle",
    "stop_cancelled": "idle",
    "StopFailure": "error",
    "stop_failure": "error",
    "SessionEnd": "idle",
    "session_end": "idle",
}

NOTIFY_STATE = {
    "approval_required": "attention",
    "permission_prompt": "attention",
    "agent_error": "error",
    "idle_prompt": "idle",
}

CLI_STATES = {"busy", "attention", "error", "idle"}


def _get(data: dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return str(value)
    return default


def _event_name(data: dict[str, Any]) -> str:
    return _get(data, "hook_event_name", "hookEventName")


def apply_payload(data: dict[str, Any], *, source: str) -> None:
    if _get(data, "subagentType", "subagent_type"):
        return
    event = _event_name(data)
    ntype = _get(data, "notification_type", "notificationType", "type").lower()
    state = ""
    force = event in {"SessionEnd", "session_end"}
    if event in {"Notification", "notification"}:
        state = NOTIFY_STATE.get(ntype, "")
    else:
        state = EVENT_STATE.get(event, "")
    if not state:
        return
    sid = _get(data, "sessionId", "session_id") or "unknown"
    prompt_id = _get(data, "promptId", "prompt_id")
    if state == "idle" and ntype == "idle_prompt":
        prev = (load_state().get("sessions") or {}).get(sid) or {}
        if prev.get("state") in {"attention", "error"}:
            return
    update_session(
        sid,
        state=state,
        prompt_id=prompt_id,
        source=source,
        event=event or ntype,
        force=force,
    )


def apply_cli(state: str, session_id: str, source: str, event: str) -> None:
    if state not in CLI_STATES:
        raise ValueError(f"state must be one of {sorted(CLI_STATES)}")
    update_session(
        session_id or "manual",
        state=state,
        source=source,
        event=event,
        force=True,
    )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        if args[:1] == ["--notify"]:
            grok_event = os.environ.get("GROK_EVENT", "").strip().lower()
            state = NOTIFY_STATE.get(grok_event, "")
            if state:
                apply_cli(
                    state,
                    os.environ.get("GROK_SESSION_ID", "grok-notify"),
                    "notify",
                    grok_event,
                )
            return 0
        if args[:1] == ["--event"] and len(args) >= 2:
            sid = args[2] if len(args) > 2 else "manual"
            apply_cli(args[1], sid, "cli", args[1])
            return 0
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        data = json.loads(raw)
        if isinstance(data, dict):
            apply_payload(data, source="hook")
    except Exception:  # noqa: BLE001 — hooks must fail open, never block a turn
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
