#!/usr/bin/env python3
"""PostCompact: mine Grok compaction/INDEX.md as a palace pointer.

Selective model filing (rule mempalace-compact-filing) is the source of
truth. This hook only stages the small INDEX plus a session pointer so
later search can find the on-disk segment_*.md files. It does not mine
those segments (skill-list noise). Fail-open on every error.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

MARKER_DIR = Path.home() / ".cache" / "mempalace-compact-index"
STAGING_ROOT = Path.home() / ".mempalace" / "staging"
GROK_SESSIONS = Path.home() / ".grok" / "sessions"


def _fail_open() -> int:
    return 0


def session_id_from(payload: dict[str, Any]) -> str:
    raw = payload.get("sessionId") or payload.get("session_id") or ""
    return str(raw).strip()


def transcript_path_from(payload: dict[str, Any]) -> Path | None:
    raw = payload.get("transcriptPath") or payload.get("transcript_path") or ""
    text = str(raw).strip()
    if not text:
        return None
    return Path(text).expanduser()


def find_index(session_id: str, transcript: Path | None) -> Path | None:
    candidates: list[Path] = []
    if transcript is not None:
        base = transcript if transcript.is_dir() else transcript.parent
        candidates.append(base / "compaction" / "INDEX.md")
        if base.name == "compaction":
            candidates.append(base / "INDEX.md")
    sid = session_id.strip()
    if sid and GROK_SESSIONS.is_dir():
        candidates.extend(GROK_SESSIONS.glob(f"*/{sid}/compaction/INDEX.md"))
    seen: set[Path] = set()
    for cand in candidates:
        try:
            resolved = cand.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file():
            return resolved
    return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def already_mined(session_id: str, digest: str) -> bool:
    if not session_id:
        return False
    marker = MARKER_DIR / f"{session_id}.sha256"
    if not marker.is_file():
        return False
    return marker.read_text(encoding="utf-8").strip() == digest


def write_marker(session_id: str, digest: str) -> None:
    if not session_id:
        return
    MARKER_DIR.mkdir(parents=True, exist_ok=True)
    (MARKER_DIR / f"{session_id}.sha256").write_text(digest + "\n", encoding="utf-8")


def pointer_markdown(session_id: str, index_path: Path, index_body: str) -> str:
    compact_dir = index_path.parent
    today = date.today().isoformat()
    phrase = (
        "compaction-time MemPalace INDEX pointer "
        f"session {session_id or 'unknown'} {today}"
    )
    return (
        "# Compaction index pointer\n"
        "kind: session-continuity\n"
        f"as_of: {today}\n"
        "status: current\n"
        f"session_id: {session_id or 'unknown'}\n"
        f"compaction_dir: {compact_dir}\n"
        f"unique: {phrase}\n"
        "\n"
        "Full turn text stays on disk in segment_*.md next to INDEX.md. "
        "Do not treat the compact summary as filing. Lookup keys live in "
        "palace drawers the model filed (rule mempalace-compact-filing).\n"
        "\n"
        "## INDEX.md\n"
        "\n"
        f"{index_body.rstrip()}\n"
    )


def enqueue_mine(stage: Path, wing: str) -> None:
    agent = os.environ.get("USER") or os.environ.get("LOGNAME") or "agent"
    cmd = [
        "mempalace",
        "mine",
        str(stage),
        "--mode",
        "projects",
        "--wing",
        wing,
        "--agent",
        agent,
        "--daemon",
        "--background",
    ]
    subprocess.run(cmd, check=False, timeout=15, capture_output=True)


def run(payload: dict[str, Any]) -> int:
    try:
        session_id = session_id_from(payload)
        index_path = find_index(session_id, transcript_path_from(payload))
        if index_path is None:
            return _fail_open()
        digest = sha256_file(index_path)
        if already_mined(session_id, digest):
            return _fail_open()
        body = index_path.read_text(encoding="utf-8", errors="replace")
        today = date.today().isoformat()
        short = (session_id or "session")[:8]
        stage = STAGING_ROOT / f"{today}-compact-{short}"
        stage.mkdir(parents=True, exist_ok=True)
        (stage / "compact-index.md").write_text(
            pointer_markdown(session_id, index_path, body), encoding="utf-8"
        )
        wing = os.environ.get("MEMPALACE_COMPACT_WING") or "personal"
        enqueue_mine(stage, wing)
        write_marker(session_id, digest)
    except (OSError, TypeError, ValueError, subprocess.SubprocessError, TimeoutError):
        return _fail_open()
    return _fail_open()


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload: dict[str, Any]
        if not raw.strip():
            payload = {}
        else:
            loaded = json.loads(raw)
            payload = loaded if isinstance(loaded, dict) else {}
        return run(payload)
    except (
        OSError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
        subprocess.SubprocessError,
        TimeoutError,
        UnicodeError,
    ):
        return _fail_open()


if __name__ == "__main__":
    raise SystemExit(main())
