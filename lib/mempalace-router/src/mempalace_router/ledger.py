"""SQLite write ledger and offline outbox for mempalace-router.

``Ledger`` records which remote/local refs a routed write produced.
``Outbox`` queues writes for a target that is unreachable and replays them
in order. Both classes may share one database file.
"""

import json
import sqlite3
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

_STALE_MARKERS = ("not current", "no current fact")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(path: Path) -> sqlite3.Connection:
    # Autocommit so separate connections on one file never hold write locks
    # across calls; the Router calls from a thread pool.
    conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


class Ledger:
    """Record of routed writes, searchable by any of their reference ids."""

    def __init__(self, path: Path):
        """Open (creating if needed) the ledger table in the database at path."""
        self._lock = threading.Lock()
        self._conn = _connect(Path(path))
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS ledger ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, call_id TEXT, "
            "mine_job_id TEXT, target TEXT, tool TEXT, local_ref TEXT, "
            "remote_ref TEXT, payload_json TEXT)"
        )

    def close(self) -> None:
        """Close the underlying connection."""
        with self._lock:
            self._conn.close()

    def record(
        self,
        *,
        call_id,
        target,
        tool,
        local_ref,
        remote_ref,
        payload: dict,
        mine_job_id=None,
    ) -> int:
        """Insert a ledger row and return its id."""
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO ledger (created_at, call_id, mine_job_id, target, tool, "
                "local_ref, remote_ref, payload_json) VALUES (?,?,?,?,?,?,?,?)",
                (
                    _now(),
                    call_id,
                    mine_job_id,
                    target,
                    tool,
                    local_ref,
                    remote_ref,
                    json.dumps(payload),
                ),
            )
            return int(cur.lastrowid)

    def lookup(self, ref: str) -> list[dict]:
        """Return rows whose call_id, mine_job_id, local_ref or remote_ref equals ref."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM ledger WHERE call_id=? OR mine_job_id=? OR local_ref=? "
                "OR remote_ref=? ORDER BY id",
                (ref, ref, ref, ref),
            ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json") or "{}")
            out.append(item)
        return out

    def forget(self, row_ids: list[int]) -> None:
        """Delete the ledger rows with the given ids."""
        if not row_ids:
            return
        with self._lock:
            self._conn.executemany("DELETE FROM ledger WHERE id=?", [(i,) for i in row_ids])


class Outbox:
    """FIFO queue of writes awaiting delivery to an unreachable target."""

    def __init__(self, path: Path):
        """Open (creating if needed) the outbox table in the database at path."""
        self._lock = threading.Lock()
        self._conn = _connect(Path(path))
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS outbox ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, target TEXT, "
            "tool TEXT, arguments_json TEXT, local_ref TEXT, call_id TEXT, "
            "attempts INTEGER DEFAULT 0, last_error TEXT)"
        )

    def close(self) -> None:
        """Close the underlying connection."""
        with self._lock:
            self._conn.close()

    def enqueue(self, *, target, tool, arguments: dict, local_ref, call_id) -> int:
        """Queue a write and return its row id."""
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO outbox (created_at, target, tool, arguments_json, "
                "local_ref, call_id, attempts) VALUES (?,?,?,?,?,?,0)",
                (_now(), target, tool, json.dumps(arguments), local_ref, call_id),
            )
            return int(cur.lastrowid)

    def pending(self, target: str) -> list[dict]:
        """Return queued rows for target, oldest first."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM outbox WHERE target=? ORDER BY id", (target,)
            ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["arguments"] = json.loads(item.pop("arguments_json") or "{}")
            out.append(item)
        return out

    def _delete(self, row_id: int) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM outbox WHERE id=?", (row_id,))

    def _fail(self, row_id: int, error: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE outbox SET attempts=attempts+1, last_error=? WHERE id=?",
                (error, row_id),
            )

    def drain(
        self,
        target: str,
        send: Callable[[str, dict], dict],
        on_pushed: Callable[[dict, dict], None] | None = None,
    ) -> dict:
        """Replay pending rows for target in order through send(tool, arguments).

        A successful result deletes the row and calls ``on_pushed(row, result)``.
        A result dict with ``success`` false whose ``error`` contains "not
        current" or "no current fact" (case-insensitive) is stale: the row is
        deleted and counted ``skipped_stale``. A transport exception, or any
        other ``success`` false result (logical rejection), increments
        ``attempts``, stores ``last_error``, counts ``failed``, appends the
        error and STOPS the drain so order is preserved; later rows stay
        pending.

        Returns ``{"pushed", "skipped_stale", "failed", "errors"}``.
        """
        result = {"pushed": 0, "skipped_stale": 0, "failed": 0, "errors": []}
        for row in self.pending(target):
            try:
                reply = send(row["tool"], row["arguments"])
            except Exception as exc:  # transport failure: keep row, stop
                self._fail(row["id"], str(exc))
                result["failed"] += 1
                result["errors"].append(str(exc))
                break
            if isinstance(reply, dict) and reply.get("success") is False:
                error = str(reply.get("error", ""))
                if any(marker in error.lower() for marker in _STALE_MARKERS):
                    self._delete(row["id"])
                    result["skipped_stale"] += 1
                    continue
                self._fail(row["id"], error)
                result["failed"] += 1
                result["errors"].append(error)
                break
            self._delete(row["id"])
            result["pushed"] += 1
            if on_pushed is not None:
                on_pushed(row, reply)
        return result
