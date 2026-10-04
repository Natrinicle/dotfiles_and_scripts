"""Atomic session-tunes state file (hooks write, daemon reads)."""

from __future__ import annotations

import fcntl
import json
import os
import time
from pathlib import Path
from typing import Any

STATES = ("idle", "busy", "attention", "error")
PRIORITY = {"idle": 0, "busy": 1, "attention": 2, "error": 3}

CACHE_DIR = Path.home() / ".cache" / "session-tunes"
STATE_PATH = CACHE_DIR / "state.json"
LOCK_PATH = CACHE_DIR / "state.lock"


def _ensure_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def empty_state() -> dict[str, Any]:
    return {"sessions": {}}


def load_state() -> dict[str, Any]:
    _ensure_dir()
    if not STATE_PATH.exists():
        return empty_state()
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_state()
    if not isinstance(data, dict) or "sessions" not in data:
        return empty_state()
    return data


def save_state(data: dict[str, Any]) -> None:
    _ensure_dir()
    tmp = STATE_PATH.with_suffix(".tmp")
    blob = json.dumps(data, indent=2, sort_keys=True) + "\n"
    tmp.write_text(blob, encoding="utf-8")
    tmp.replace(STATE_PATH)


def update_session(
    session_id: str,
    *,
    state: str,
    prompt_id: str = "",
    source: str = "hook",
    event: str = "",
    force: bool = False,
) -> None:
    if state not in STATES:
        raise ValueError(f"bad state {state}")
    session_id = session_id or "unknown"
    _ensure_dir()
    with LOCK_PATH.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        data = load_state()
        sessions: dict[str, Any] = data.setdefault("sessions", {})
        prev = sessions.get(session_id) or {}
        # A cancelled Stop can arrive after the next UserPromptSubmit.
        if (
            not force
            and state == "idle"
            and prompt_id
            and prev.get("prompt_id")
            and prev.get("prompt_id") != prompt_id
        ):
            return
        sessions[session_id] = {
            "state": state,
            "prompt_id": prompt_id or prev.get("prompt_id") or "",
            "source": source,
            "event": event,
            "updated_at": time.time(),
            "pid": os.getpid(),
        }
        cutoff = time.time() - 7200
        data["sessions"] = {
            sid: rec
            for sid, rec in sessions.items()
            if float(rec.get("updated_at") or 0) >= cutoff
        }
        save_state(data)


def aggregate(data: dict[str, Any] | None = None) -> str:
    data = data or load_state()
    best = "idle"
    now = time.time()
    for rec in (data.get("sessions") or {}).values():
        if now - float(rec.get("updated_at") or 0) > 1800:
            continue
        st = rec.get("state") or "idle"
        if PRIORITY.get(st, 0) > PRIORITY[best]:
            best = st
    return best
