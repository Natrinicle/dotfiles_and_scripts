"""Scope-routed JSON-RPC dispatcher in front of a local hub and company hubs.

``Router.handle`` takes one JSON-RPC request and returns the response. Reads
fan out to the targets in scope, writes go to local first and then to at most
one company, and the ``router_*`` tools live in :mod:`router_tools`.
"""

import copy
import fcntl
import json
import logging
import os
import re
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor, wait
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from mempalace_router import merge, router_tools
from mempalace_router.client import HubClient, HubError
from mempalace_router.config import Targets
from mempalace_router.content_guard import find_secret
from mempalace_router.ledger import KG_ADD, SUPERSEDE, Ledger, Outbox, supersede_fallback_args
from mempalace_router.results import is_stale_error, result_error, result_failed
from mempalace_router.router_tools import RpcError
from mempalace_router.scope import ScopeError, normalize_scope
from mempalace_router.taxonomy import TaxonomyMap, canonical

log = logging.getLogger(__name__)

READ_TOOLS = frozenset(
    {
        "mempalace_status", "mempalace_list_wings", "mempalace_list_rooms", "mempalace_get_taxonomy",
        "mempalace_kg_query", "mempalace_kg_timeline", "mempalace_kg_stats", "mempalace_graph_stats",
        "mempalace_search", "mempalace_check_duplicate", "mempalace_list_drawers",
    }
)
WRITE_TOOLS = frozenset(
    {
        "mempalace_add_drawer", "mempalace_kg_add", "mempalace_kg_supersede", "mempalace_kg_invalidate",
        "mempalace_diary_write",
    }
)
LOCAL_ONLY_TOOLS = frozenset(
    "mempalace_" + n
    for n in (
        "mine sync reconnect hook_settings mesh_peers get_aaak_spec checkpoint patch_submit "
        "artifact_put artifact_get event_append event_ack event_list event_wait task_create "
        "create_tunnel delete_tunnel delete_hallway list_tunnels list_hallways find_tunnels "
        "follow_tunnels traverse memories_filed_away diary_read"
    ).split()
)
# Drawer ids are per palace: usable on local only, never with a company in scope.
ID_BOUND_TOOLS = frozenset(
    {
        "mempalace_delete_drawer", "mempalace_delete_drawers", "mempalace_update_drawer",
        "mempalace_delete_by_source", "mempalace_get_drawer", "mempalace_get_drawers",
    }
)
LEDGERED_TOOLS = frozenset({"mempalace_add_drawer", "mempalace_kg_add", "mempalace_kg_supersede"})
GUARDED_FIELDS = ("content", "object", "new_object", "entry")
SCOPE_SCHEMA = {
    "type": "array",
    "items": {"type": "string"},
    "description": "Targets: local always included; at most one company",
}
ROUTER_TOOLS = {
    "router_targets": router_tools.tool_targets,
    "router_retract": router_tools.tool_retract,
    "router_replicate": router_tools.tool_replicate,
    "router_flush": router_tools.tool_flush,
    "router_status": router_tools.tool_status,
}


def iso_now() -> str:
    """Current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _ref(tool: str, result: dict):
    return result.get("drawer_id") if tool == "mempalace_add_drawer" else result.get("triple_id")


_failed = result_failed
FALLBACK_NOTE = "added (no prior fact)"


def _strings(value) -> Iterator[str]:
    """Every string inside a JSON-like value (dict values, list items)."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)


class Router:
    """Dispatch JSON-RPC requests across the configured hub targets."""

    def __init__(
        self,
        targets: Targets,
        *,
        state_dir: Path,
        clients: dict[str, HubClient] | None = None,
        per_target_timeout_s: float = 30.0,
        now: Callable[[], str] = iso_now,
    ):
        self.targets = targets
        self.local_name = targets.local.name
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.state_dir / "router.sqlite3"
        self.ledger = Ledger(self.db_path)
        self.outbox = Outbox(self.db_path)
        self.timeout_s = per_target_timeout_s
        self.now = now
        self._clients: dict[str, HubClient] = dict(clients or {})
        self._tmaps: dict[str, TaxonomyMap] = {}
        self._remote_tax: dict[str, dict] = {}
        self._drain_locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()
        self.single_valued = frozenset(targets.single_valued_predicates)

    def close(self) -> None:
        """Close the ledger and outbox connections."""
        self.ledger.close()
        self.outbox.close()

    # -- shared plumbing ------------------------------------------------

    def client(self, name: str) -> HubClient:
        """Return (lazily creating) the hub client for a target."""
        with self._guard:
            if name not in self._clients:
                self._clients[name] = HubClient(self.targets.by_name[name], timeout_s=self.timeout_s)
            return self._clients[name]

    def drain_lock(self, name: str) -> threading.Lock:
        """Per-target in-process lock serialising outbox drains."""
        with self._guard:
            return self._drain_locks.setdefault(name, threading.Lock())

    def lock_path(self, name: str) -> Path:
        """Cross-process drain lock file for a target."""
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
        return self.state_dir / "locks" / f"drain-{safe}.lock"

    @contextmanager
    def drain_guard(self, name: str) -> Iterator[bool]:
        """Hold the target's drain lock (thread lock plus ``flock``); yield whether it was taken.

        Several router processes (each stdio session plus the HTTP unit)
        share one state dir, so the outbox for a target is drained, dequeued
        or bypassed only under an exclusive ``flock`` on
        ``state_dir/locks/drain-<target>.lock``. Waits at most
        ``per_target_timeout_s``; on timeout yields ``False`` and the caller
        must not touch the target's outbox or send around it.
        """
        deadline = time.monotonic() + self.timeout_s
        tlock = self.drain_lock(name)
        if not tlock.acquire(timeout=self.timeout_s):
            yield False
            return
        try:
            path = self.lock_path(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
            try:
                while True:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        if time.monotonic() >= deadline:
                            yield False
                            return
                        time.sleep(0.02)
                try:
                    yield True
                finally:
                    fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)
        finally:
            tlock.release()

    def taxmap(self, name: str) -> TaxonomyMap:
        """Return the (lazily loaded) taxonomy map for a company target."""
        with self._guard:
            tmap = self._tmaps.get(name)
            if tmap is None:
                tmap = TaxonomyMap(name, self.state_dir)
                tmap.load()
                self._tmaps[name] = tmap
            return tmap

    def fan_out(self, names: list[str], fn: Callable[[str], object]) -> dict[str, tuple[bool, object]]:
        """Run ``fn(name)`` per target in threads; ``{name: (ok, value_or_exc)}``.

        A target that exceeds ``per_target_timeout_s`` yields a ``timeout``
        HubError. Threads are joined unless one timed out; a straggler is
        bounded by the hub client's own timeout.
        """
        out: dict[str, tuple[bool, object]] = {}
        if not names:
            return out
        pool = ThreadPoolExecutor(max_workers=len(names))
        futures = {pool.submit(fn, n): n for n in names}
        done, pending = wait(futures, timeout=self.timeout_s)
        for fut, name in futures.items():
            if fut in done:
                try:
                    out[name] = (True, fut.result())
                except Exception as exc:
                    out[name] = (False, exc)
            else:
                fut.cancel()
                out[name] = (False, HubError("timeout", f"{name} exceeded {self.timeout_s}s"))
        pool.shutdown(wait=not pending, cancel_futures=True)
        return {n: out[n] for n in names}

    def pending_counts(self) -> dict[str, int]:
        """Queued outbox rows per company target."""
        return {n: self.outbox.count(n) for n in self.targets.companies}

    # -- taxonomy mapping ----------------------------------------------

    def _remote_taxonomy(self, name: str) -> dict:
        """Company taxonomy; cached only when the reply is a real taxonomy."""
        cached = self._remote_tax.get(name)
        if cached is None:
            reply = self.client(name).call_tool("mempalace_get_taxonomy", {})
            taxonomy = reply.get("taxonomy")
            if reply.get("success") is False or not isinstance(taxonomy, dict):
                raise HubError("rpc", "taxonomy unavailable")
            cached = self._remote_tax[name] = taxonomy
        return cached

    @staticmethod
    def _unmapped_note(name: str) -> str:
        return f"taxonomy unavailable for {name}; names unmapped"

    def map_wing_room(self, name: str, wing: str, room: str, notes: list | None = None) -> tuple[str, str]:
        """Map a local wing/room to a company target's names.

        When the company taxonomy cannot be fetched, no alias is recorded and
        the names pass through unmapped (a note says so).
        """
        tmap = self.taxmap(name)
        known_wing, known_room = tmap.known(wing, room)
        if known_wing and known_room:
            return known_wing, known_room
        try:
            taxonomy = self._remote_taxonomy(name)
        except HubError:
            if notes is not None:
                notes.append(self._unmapped_note(name))
            return known_wing or wing, known_room or room
        rw, rr, created = tmap.to_remote(wing, room, taxonomy)
        if created:
            self._remote_tax.pop(name, None)
        return rw, rr

    def _map_wing(self, name: str, wing: str, notes: list | None) -> str:
        known, _ = self.taxmap(name).known(wing)
        if known:
            return known
        try:
            taxonomy = self._remote_taxonomy(name)
        except HubError:
            if notes is not None:
                notes.append(self._unmapped_note(name))
            return wing
        return next((w for w in sorted(taxonomy) if canonical(w) == canonical(wing)), wing)

    def map_args(self, name: str, args: dict, notes: list | None = None) -> dict:
        """Return a copy of ``args`` with wing/room mapped for a company target."""
        mapped = dict(args)
        if name == self.local_name or not isinstance(args.get("wing"), str):
            return mapped
        if isinstance(args.get("room"), str):
            mapped["wing"], mapped["room"] = self.map_wing_room(name, args["wing"], args["room"], notes)
        else:
            mapped["wing"] = self._map_wing(name, args["wing"], notes)
        return mapped

    def _to_local(self, target: str, wing, room):
        if target == self.local_name or not isinstance(wing, str) or not isinstance(room, str):
            return wing, room
        return self.taxmap(target).to_local(wing, room)

    # -- company writes -------------------------------------------------

    def write_company(
        self, name, tool, args, *, local_ref, call_id, mine_job_id=None, skip_send=False
    ) -> dict:
        """Write to one company target; outcome ``{"status": filed|queued|partial|refused, ...}``.

        Sent directly with the client's own timeout (never retried here).
        When rows are already queued for the target, the outbox is drained
        first under the drain guard; the write is sent directly only if the
        queue is then empty, otherwise it is queued behind the rest so order
        is kept. A ``kg_supersede`` the company refuses because it lacks the
        old fact falls back to ``kg_add`` of the new object (outcome
        ``fallback: "added (no prior fact)"``).
        """
        for field in GUARDED_FIELDS:
            value = args.get(field)
            if isinstance(value, str):
                hit = find_secret(value)
                if hit:
                    return {"status": "refused", "reason": f"secret_pattern:{hit}"}
        notes: list[str] = []
        try:
            mapped = self.map_args(name, args, notes)
        except Exception as exc:  # corrupt taxonomy file etc.
            return {"status": "partial", "error": str(exc)}

        def done(outcome: dict) -> dict:
            if notes:
                outcome["notes"] = notes
            return outcome

        def queue():
            self.outbox.enqueue(
                target=name, tool=tool, arguments=mapped, local_ref=local_ref, call_id=call_id
            )
            return done({"status": "queued"})

        def send() -> dict:
            return done(self._send_company(name, tool, mapped, local_ref, call_id, mine_job_id, queue))

        if skip_send:
            return queue()
        if not self.outbox.count(name):
            return send()
        with self.drain_guard(name) as held:
            if not held:
                return queue()
            try:
                self._drain_locked(name)
            except Exception:
                log.exception("auto-drain of %s failed", name)
            if self.outbox.count(name):
                return queue()
            return send()

    def _send_company(self, name, tool, mapped, local_ref, call_id, mine_job_id, queue) -> dict:
        """Send one write directly; queue on transport failure; ledger on success."""
        client = self.client(name)
        fallback = False
        try:
            value = client.call_tool(tool, mapped)
            if _failed(value) and tool == SUPERSEDE and is_stale_error(result_error(value)):
                add_args = supersede_fallback_args(mapped)
                value = client.call_tool(KG_ADD, add_args)
                tool, mapped, fallback = KG_ADD, add_args, True
        except HubError as exc:
            if exc.kind in ("transport", "timeout"):
                return queue()
            return {"status": "partial", "error": str(exc)}
        except Exception as exc:
            return {"status": "partial", "error": str(exc)}
        if _failed(value):
            error = result_error(value)
            if "wing" in error.lower() or "room" in error.lower():
                self._remote_tax.pop(name, None)
            return {"status": "partial", "error": error}
        remote_ref = _ref(tool, value)
        if tool in LEDGERED_TOOLS:
            if not remote_ref:
                return {"status": "partial", "error": "no remote id"}
            self.ledger.record(
                call_id=call_id, target=name, tool=tool, local_ref=local_ref,
                remote_ref=remote_ref, payload=mapped, mine_job_id=mine_job_id,
            )
        outcome = {"status": "filed", "remote_ref": remote_ref}
        if fallback:
            outcome["fallback"] = FALLBACK_NOTE
        return outcome

    def _drain_locked(self, name: str) -> dict:
        """Drain a target's outbox; the caller holds :meth:`drain_guard`."""
        client = self.client(name)

        def on_pushed(row: dict, reply: dict) -> None:
            if row["tool"] in LEDGERED_TOOLS and _ref(row["tool"], reply):
                self.ledger.record(
                    call_id=row["call_id"], target=name, tool=row["tool"], local_ref=row["local_ref"],
                    remote_ref=_ref(row["tool"], reply), payload=row["arguments"],
                )

        return self.outbox.drain(name, lambda tool, a: client.call_tool(tool, a), on_pushed=on_pushed)

    def flush(self, name: str) -> dict:
        """Drain a company target's outbox under the cross-process drain guard."""
        with self.drain_guard(name) as held:
            if not held:
                return {"pushed": 0, "skipped_stale": 0, "fallback_add": 0, "failed": 0,
                        "errors": ["drain lock busy"]}
            return self._drain_locked(name)

    def flush_all(self) -> None:
        """Drain every company outbox, logging (not raising) failures. For startup."""
        for name in self.targets.companies:
            try:
                self.flush(name)
            except Exception:
                log.exception("flush of %s failed", name)

    # -- JSON-RPC -------------------------------------------------------

    def handle(self, request: dict) -> dict | None:
        """Handle one JSON-RPC request; ``None`` for notifications."""
        if not isinstance(request, dict) or "id" not in request:
            return None
        rid = request["id"]
        try:
            params = request.get("params")
            if params is None:
                params = {}
            if not isinstance(params, dict):
                raise RpcError(-32602, "params must be an object")
            result = self._dispatch(request.get("method"), params)
        except RpcError as exc:
            error = {"code": exc.code, "message": exc.message}
            if exc.data is not None:
                error["data"] = exc.data
            return {"jsonrpc": "2.0", "id": rid, "error": error}
        except Exception as exc:
            log.exception("router internal error")
            return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32603, "message": f"internal error: {exc}"}}
        return {"jsonrpc": "2.0", "id": rid, "result": result}

    def _local(self, fn):
        try:
            return fn(self.client(self.local_name))
        except HubError as exc:
            raise RpcError(-32000, "local_unreachable", {"detail": str(exc)}) from exc

    def _dispatch(self, method, params: dict) -> dict:
        if method == "initialize":
            result = copy.deepcopy(self._local(lambda c: c._rpc("initialize", params)))
            result.setdefault("serverInfo", {})["name"] = "mempalace-router"
            return result
        if method == "tools/list":
            tools = copy.deepcopy(self._local(lambda c: c.list_tools()))
            for tool in tools:
                if str(tool.get("name", "")).startswith("mempalace_"):
                    schema = tool.setdefault("inputSchema", {"type": "object"})
                    schema.setdefault("properties", {})["scope"] = dict(SCOPE_SCHEMA)
            return {"tools": tools + router_tools.router_tool_descriptors()}
        if method == "tools/call":
            name, args = params.get("name"), params.get("arguments") or {}
            if not isinstance(name, str) or not isinstance(args, dict):
                raise RpcError(-32602, "tools/call needs a tool name and object arguments")
            return {"content": [{"type": "text", "text": json.dumps(self._call_tool(name, dict(args)))}]}
        raise RpcError(-32601, f"method not found: {method}")

    def _scope(self, args: dict) -> tuple[list[str], list[str]]:
        scope = args.pop("scope", None)
        if scope is not None and not (isinstance(scope, list) and all(isinstance(s, str) for s in scope)):
            raise RpcError(-32602, "scope must be a list of target names")
        try:
            names, notes = normalize_scope(scope, self.targets)
        except ScopeError as exc:
            raise RpcError(-32602, str(exc), {"code": exc.code}) from exc
        if len(names) > 2:  # distinct companies are already rejected, so these share one
            raise RpcError(-32602, "one target per company in scope")
        return names, notes

    def _call_tool(self, name: str, args: dict) -> dict:
        if name == "router_mine":
            names, _ = self._scope(args)
            return router_tools.tool_mine(self, args, names)
        if name in ROUTER_TOOLS:
            return ROUTER_TOOLS[name](self, args)
        if not name.startswith("mempalace_"):
            raise RpcError(-32602, f"unknown tool: {name}")
        had_scope = "scope" in args
        known = name in READ_TOOLS or name in WRITE_TOOLS or name in ID_BOUND_TOOLS
        if name in LOCAL_ONLY_TOOLS or not known:
            args.pop("scope", None)
            result = dict(self._local(lambda c: c.call_tool(name, args)))
            if name not in LOCAL_ONLY_TOOLS:
                self._add_notes(result, ["unknown tool routed local-only"])
            elif had_scope:
                self._add_notes(result, ["scope ignored for local-only tool"])
            return result
        names, notes = self._scope(args)
        if name in ID_BOUND_TOOLS:
            if len(names) > 1:
                raise RpcError(-32602, "ids are per-palace; use router_retract / local scope")
            result = dict(self._local(lambda c: c.call_tool(name, args)))
        elif name in WRITE_TOOLS:
            result = self._write(name, args, names)
        else:
            result = self._read(name, args, names, notes)
        self._add_notes(result, notes)
        return result

    @staticmethod
    def _add_notes(result: dict, notes: list[str]) -> None:
        if notes:
            existing = result.get("notes")
            result["notes"] = (existing if isinstance(existing, list) else []) + notes

    # -- reads ------------------------------------------------------------

    def _read(self, name: str, args: dict, names: list[str], notes: list[str]) -> dict:
        refused: dict[str, str] = {}
        hit = next((h for h in map(find_secret, _strings(args)) if h), None)
        if hit:  # never send a secret-looking query or payload off the machine
            for target in names:
                if target != self.local_name:
                    refused[target] = f"secret_pattern:{hit}"
                    notes.append(f"{target} not queried: an argument matched secret_pattern:{hit}")
            names = [n for n in names if n not in refused]
        raw = self.fan_out(names, lambda n: self.client(n).call_tool(name, self.map_args(n, args, notes)))
        local_ok, local_value = raw[self.local_name]
        if not local_ok:
            raise RpcError(-32000, "local_unreachable", {"detail": str(local_value)})
        good = {n: v for n, (ok, v) in raw.items() if ok and not (n != self.local_name and _failed(v))}
        degraded = [n for n in names if n not in good]
        company = next((n for n in names if n != self.local_name), None)
        if name == "mempalace_search":
            result = merge.merge_search(good, self._to_local)
        elif name == "mempalace_kg_query":
            result, conflicts = merge.merge_kg_query(good, company=company if company in good else None,
                                                     local=self.local_name, single_valued=self.single_valued)
            result["conflicts"] = conflicts
            if conflicts and "as_of" not in args:
                result["corrections"] = self._correct(conflicts, company)
        else:
            result = dict(local_value)
            result["by_target"] = good
        if degraded:
            result["degraded"] = degraded
        if refused:
            result["refused"] = refused
        return result

    def _correct(self, conflicts: list[dict], company: str) -> list[dict]:
        """Supersede the older side of each actionable kg_query conflict.

        Only conflicts on ``single_valued_predicates`` carry an action (see
        :func:`merge.merge_kg_query`); the rest are reported, not corrected.
        """
        corrections = []
        for conflict in conflicts:
            if conflict["action"] == "none":
                continue
            loser_local = conflict["action"] == "supersede_local"
            loser = self.local_name if loser_local else company
            old = conflict["local" if loser_local else "company"].get("object")
            new = conflict["company" if loser_local else "local"].get("object")
            entry = {"subject": conflict["subject"], "predicate": conflict["predicate"], "target": loser,
                     "old_object": old, "new_object": new, "applied": False}
            call = {"subject": conflict["subject"], "predicate": conflict["predicate"],
                    "old_object": old, "new_object": new}
            if loser_local:
                try:
                    reply = self.client(loser).call_tool("mempalace_kg_supersede", call)
                    if _failed(reply):
                        entry["error"] = str(reply.get("error", "failed"))
                    else:
                        entry["applied"] = True
                except HubError as exc:
                    entry["error"] = str(exc)
                except Exception as exc:  # e.g. corrupt state; record, never raise from a read
                    entry["error"] = str(exc)
            else:  # company side: guard, ledger and outbox semantics apply
                outcome = self.write_company(
                    loser, "mempalace_kg_supersede", call, local_ref=None, call_id=uuid.uuid4().hex
                )
                entry["status"] = outcome["status"]
                if outcome["status"] == "filed":
                    entry["applied"] = True
                    if outcome.get("fallback"):
                        entry["fallback"] = outcome["fallback"]
                else:
                    entry["error"] = outcome.get("error") or outcome.get("reason") or outcome["status"]
            corrections.append(entry)
        return corrections

    # -- writes -----------------------------------------------------------

    def _write(self, name: str, args: dict, names: list[str]) -> dict:
        call_id = uuid.uuid4().hex
        result = dict(self._local(lambda c: c.call_tool(name, args)))
        company = next((n for n in names if n != self.local_name), None)
        if company is None:
            return result
        if _failed(result):
            result["company_skipped"] = "local write failed"
            return result
        local_ref = _ref(name, result)
        outcome = self.write_company(company, name, args, local_ref=local_ref, call_id=call_id)
        result["call_id"] = call_id
        self._add_notes(result, outcome.get("notes", []))
        status = outcome["status"]
        if status == "refused":
            result["refused"] = {company: outcome["reason"]}
        elif status == "queued":
            result["queued_for"] = [company]
        elif status == "partial":
            result["partial"] = {company: outcome["error"]}
        else:
            result["filed_to"] = [self.local_name, company]
            result["tag"] = f"filed → {company} + local"
            if outcome.get("fallback"):
                result["fallback"] = {company: outcome["fallback"]}
                self._add_notes(result, [f"{company}: {outcome['fallback']}"])
        return result
