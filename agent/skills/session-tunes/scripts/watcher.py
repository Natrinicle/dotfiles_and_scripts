"""Light C fallback: infer busy from live Grok/Claude session activity."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

GROK_ACTIVE = Path.home() / ".grok" / "active_sessions.json"
GROK_SESSIONS = Path.home() / ".grok" / "sessions"
CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"


def _pid_alive(pid: int) -> bool:
    if pid <= 1:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _newest_mtime(path: Path) -> float:
    newest = 0.0
    if not path.exists():
        return newest
    if path.is_file():
        try:
            return path.stat().st_mtime
        except OSError:
            return 0.0
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules"}]
        for name in filenames:
            fp = Path(dirpath) / name
            try:
                mtime = fp.stat().st_mtime
            except OSError:
                continue
            newest = max(newest, mtime)
    return newest


def _grok_inhibit_busy() -> bool:
    """Grok holds systemd-inhibit with 'agent turn in progress' during a turn."""
    try:
        out = subprocess.run(
            ["pgrep", "-af", "systemd-inhibit"],
            capture_output=True,
            text=True,
            timeout=1,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return "agent turn in progress" in (out.stdout or "")


def _iter_grok_sessions(blob: object) -> list[tuple[str, int]]:
    rows: list[tuple[str, int]] = []
    if isinstance(blob, list):
        items = blob
    elif isinstance(blob, dict):
        items = list((blob.get("sessions") or {}).values())
        if "session_id" in blob:
            items = [blob]
    else:
        items = []
    for rec in items:
        if not isinstance(rec, dict):
            continue
        sid = str(rec.get("session_id") or rec.get("id") or "")
        pid = int(rec.get("pid") or 0)
        if sid:
            rows.append((sid, pid))
    return rows


def grok_busy_ids(activity_window_s: float) -> set[str]:
    now = time.time()
    ids: set[str] = set()
    if GROK_ACTIVE.exists():
        try:
            blob = json.loads(GROK_ACTIVE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            blob = []
        for sid, pid in _iter_grok_sessions(blob):
            if not _pid_alive(pid):
                continue
            matches = list(GROK_SESSIONS.glob(f"*/{sid}"))
            mtime = max((_newest_mtime(p) for p in matches), default=0.0)
            if now - mtime <= activity_window_s:
                ids.add(sid)
    if _grok_inhibit_busy() and not ids:
        ids.add("grok-inhibit")
    return ids


def claude_busy() -> bool:
    """True when a Claude project transcript was written very recently."""
    if not CLAUDE_PROJECTS.exists():
        return False
    now = time.time()
    newest = 0.0
    for jsonl in CLAUDE_PROJECTS.glob("*/*.jsonl"):
        try:
            mtime = jsonl.stat().st_mtime
        except OSError:
            continue
        newest = max(newest, mtime)
    return now - newest <= 6.0


def fallback_busy(activity_window_s: float = 8.0) -> bool:
    return bool(grok_busy_ids(activity_window_s)) or claude_busy()
