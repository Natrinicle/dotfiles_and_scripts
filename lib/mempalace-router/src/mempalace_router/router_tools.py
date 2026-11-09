"""``router_*`` tool handlers and their schemas.

Each handler takes the owning :class:`~mempalace_router.router.Router` and the
decoded tool arguments and returns a JSON-able dict, or raises
:class:`RpcError` for a JSON-RPC level failure.
"""

import logging
import sqlite3
import subprocess
import uuid
from contextlib import closing
from pathlib import Path

import yaml

from mempalace_router.client import HubError
from mempalace_router.results import result_failed

log = logging.getLogger(__name__)

CHUNK_CHARS = 1500
MINE_SUFFIXES = (".md", ".txt")
MINE_TIMEOUT_S = 120
TAIL_CHARS = 2000


class RpcError(Exception):
    """A JSON-RPC error to return to the caller."""

    def __init__(self, code: int, message: str, data: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


def _scope_prop(description: str = "Targets") -> dict:
    return {"type": "array", "items": {"type": "string"}, "description": description}


def router_tool_descriptors() -> list[dict]:
    """Return the ``tools/list`` entries for the router's own tools."""

    def tool(name, description, props, required=()):
        schema = {"type": "object", "properties": props}
        if required:
            schema["required"] = list(required)
        return {"name": name, "description": description, "inputSchema": schema}

    string = {"type": "string"}
    return [
        tool("router_targets", "List routing targets, reachability and queued writes.", {}),
        tool(
            "router_retract",
            "Undo company writes recorded in the ledger and drop matching queued writes "
            "(local copies are kept).",
            {"ref": string, "target": string},
            ["ref"],
        ),
        tool(
            "router_replicate",
            "Copy a local drawer or a fact to one or more company targets.",
            {
                "ref_or_fact": {"description": "Drawer id (string) or {subject, predicate, object}"},
                "to": _scope_prop("Company targets to copy to"),
            },
            ["ref_or_fact", "to"],
        ),
        tool(
            "router_mine",
            "Mine a directory into local (mempalace mine --daemon) and, by scope, chunk "
            ".md/.txt files into a company target.",
            {"dir": string, "scope": _scope_prop(), "wing": string, "room": string},
            ["dir"],
        ),
        tool("router_flush", "Push queued writes to a company target.", {"target": string}, ["target"]),
        tool("router_status", "Targets, queued writes and ledger size.", {}),
    ]


def _require_str(args: dict, key: str) -> str:
    value = args.get(key)
    if not isinstance(value, str) or not value:
        raise RpcError(-32602, f"{key} must be a non-empty string")
    return value


def _company_name(router, name, what: str = "target") -> str:
    if not isinstance(name, str) or name not in router.targets.by_name:
        raise RpcError(-32602, f"unknown {what}: {name}", {"code": "unknown_target"})
    if name == router.local_name:
        raise RpcError(-32602, f"{what} must be a company target, not local: {name}")
    return name


# -- router_targets / router_status / router_flush --------------------------


def _target_rows(router) -> list[dict]:
    names = list(router.targets.by_name)
    pings = router.fan_out(names, lambda n: router.client(n).ping())
    pending = router.pending_counts()
    rows = []
    for name in names:
        target = router.targets.by_name[name]
        ok, value = pings[name]
        aliases = 0
        if target.kind == "company":
            try:
                aliases = router.taxmap(name).alias_count()
            except ValueError:
                aliases = 0
        rows.append(
            {
                "name": name,
                "kind": target.kind,
                "company": target.company,
                "reachable": bool(ok and value),
                "outbox_pending": pending.get(name, 0),
                "taxonomy_aliases": aliases,
                "hints": target.hints,
            }
        )
    return rows


def _todo(rows: list[dict]) -> list[str]:
    return [
        f"push {row['outbox_pending']} queued writes to {row['name']} (router_flush)"
        for row in rows
        if row["outbox_pending"] > 0
    ]


def tool_targets(router, args: dict) -> dict:
    """``router_targets``: target table plus ``todo`` lines for queued writes."""
    rows = _target_rows(router)
    return {"targets": rows, "todo": _todo(rows)}


def tool_status(router, args: dict) -> dict:
    """``router_status``: targets, outbox depth, ledger size and ``todo`` lines."""
    rows = _target_rows(router)
    with closing(sqlite3.connect(str(router.db_path), timeout=30)) as conn:
        count = conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]
    return {
        "targets": rows,
        "outbox_pending": router.pending_counts(),
        "ledger_rows": count,
        "todo": _todo(rows),
        "as_of": router.now(),
    }


def tool_flush(router, args: dict) -> dict:
    """``router_flush``: drain one company target's outbox."""
    name = _company_name(router, args.get("target"))
    result = router.flush(name)
    return {"target": name, **result}


# -- router_retract ----------------------------------------------------------


def tool_retract(router, args: dict) -> dict:
    """``router_retract``: undo ledgered company writes; local copies stay.

    Rows still queued in the outbox whose ``call_id`` or ``local_ref`` equals
    ``ref`` are deleted first (under the target's drain guard) so a later
    flush cannot push them; they are counted in ``dequeued``.
    """
    ref = _require_str(args, "ref")
    target = args.get("target")
    if target is not None:
        _company_name(router, target)
    companies = [target] if target is not None else list(router.targets.companies)
    retracted_ids: list[int] = []
    by_target: dict[str, int] = {}
    errors: list[dict] = []
    dequeued = 0
    for name in companies:
        with router.drain_guard(name) as held:
            if not held:
                errors.append({"target": name, "ref": ref, "error": "drain lock busy; outbox not checked"})
                continue
            dequeued += router.outbox.delete_matching(name, ref)
    rows = [r for r in router.ledger.lookup(ref) if r["target"] in router.targets.companies]
    if target is not None:
        rows = [r for r in rows if r["target"] == target]
    for row in rows:
        name, tool, payload = row["target"], row["tool"], row["payload"]
        if tool == "mempalace_add_drawer":
            call = ("mempalace_delete_drawer", {"drawer_id": row["remote_ref"]})
        else:
            obj = payload.get("new_object") if tool == "mempalace_kg_supersede" else payload.get("object")
            call = (
                "mempalace_kg_invalidate",
                {"subject": payload.get("subject"), "predicate": payload.get("predicate"), "object": obj},
            )
        ok, value = router.fan_out([name], lambda n, c=call: router.client(n).call_tool(*c))[name]
        if not ok:
            errors.append({"target": name, "ref": row["remote_ref"], "error": str(value)})
        elif result_failed(value):
            error = value.get("error") if isinstance(value, dict) else "bad reply"
            errors.append({"target": name, "ref": row["remote_ref"], "error": str(error)})
        else:
            retracted_ids.append(row["id"])
            by_target[name] = by_target.get(name, 0) + 1
    router.ledger.forget(retracted_ids)
    return {"retracted": len(retracted_ids), "dequeued": dequeued, "by_target": by_target, "errors": errors}


# -- router_replicate --------------------------------------------------------


def tool_replicate(router, args: dict) -> dict:
    """``router_replicate``: copy a local drawer or fact to company targets."""
    to = args.get("to")
    if not isinstance(to, list) or not to or not all(isinstance(t, str) for t in to):
        raise RpcError(-32602, "to must be a non-empty list of company target names")
    names = [_company_name(router, t) for t in dict.fromkeys(to)]
    subject = args.get("ref_or_fact")
    call_id = uuid.uuid4().hex
    if isinstance(subject, str) and subject:
        try:
            drawer = router.client(router.local_name).call_tool("mempalace_get_drawer", {"drawer_id": subject})
        except HubError as exc:
            raise RpcError(-32000, "local_unreachable", {"detail": str(exc)}) from exc
        content = drawer.get("content", drawer.get("text"))
        wing, room = drawer.get("wing"), drawer.get("room")
        if drawer.get("success") is False or not isinstance(content, str) or not wing or not room:
            raise RpcError(-32602, f"drawer not found or incomplete: {subject}")
        tool, payload, local_ref = (
            "mempalace_add_drawer",
            {"wing": wing, "room": room, "content": content},
            subject,
        )
    elif isinstance(subject, dict):
        fields = ("subject", "predicate", "object")
        if not all(isinstance(subject.get(k), str) and subject.get(k) for k in fields):
            raise RpcError(-32602, "fact must have string subject, predicate and object")
        tool, payload, local_ref = "mempalace_kg_add", dict(subject), None
    else:
        raise RpcError(-32602, "ref_or_fact must be a drawer id or a fact object")
    if len(names) > 1:  # the explicit cross-company override is logged (spec invariant 2)
        ref = subject if isinstance(subject, str) else f"fact:{subject['subject']}/{subject['predicate']}"
        log.warning("cross-company replicate: %s → %s", ref, names)
    by_target = {
        name: router.write_company(name, tool, payload, local_ref=local_ref, call_id=call_id)
        for name in names
    }
    return {"call_id": call_id, "by_target": by_target}


# -- router_mine -------------------------------------------------------------


def chunk_text(text: str, limit: int = CHUNK_CHARS) -> list[str]:
    """Split text into chunks of at most ``limit`` chars on paragraph breaks."""
    chunks: list[str] = []
    current = ""
    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        while len(para) > limit:  # a single oversized paragraph is hard-split
            if current:
                chunks.append(current)
                current = ""
            chunks.append(para[:limit])
            para = para[limit:]
        joined = f"{current}\n\n{para}" if current else para
        if len(joined) <= limit:
            current = joined
        else:
            chunks.append(current)
            current = para
    if current:
        chunks.append(current)
    return chunks


def _mine_files(root: Path) -> list[Path]:
    return sorted(
        p for p in root.rglob("*") if p.suffix in MINE_SUFFIXES and p.is_file() and not p.is_symlink()
    )


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Split a leading ``---`` YAML block off ``text``; ``({}, text)`` when absent or invalid."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    try:
        meta = yaml.safe_load(text[4:end])
    except yaml.YAMLError:
        return {}, text
    rest = text[end + 4:].lstrip("\n")
    return (meta if isinstance(meta, dict) else {}), rest


def _plan_files(root: Path, wing, room) -> list[tuple[str, str, str, str]]:
    """``(relative path, wing, room, body)`` per file; arguments override frontmatter."""
    plan = []
    for path in _mine_files(root):
        rel = path.relative_to(root).as_posix()
        meta, body = split_frontmatter(path.read_text(errors="replace"))
        file_wing = wing or meta.get("wing")
        file_room = room or meta.get("room")
        if not (isinstance(file_wing, str) and file_wing and isinstance(file_room, str) and file_room):
            raise RpcError(-32602, f"wing and room required (arguments or frontmatter): {rel}")
        plan.append((rel, file_wing, file_room, body))
    return plan


def _tail(text) -> str:
    return (text or "")[-TAIL_CHARS:]


def mine_local(directory: str, wing: str | None, room: str | None) -> dict:
    """Submit a directory mine to the local write daemon via the CLI.

    The hub's MCP ``mempalace_mine`` takes the palace lock, so the local leg
    uses ``mempalace mine DIR --daemon --background`` instead. Returns
    ``{"returncode", "stdout_tail", "stderr_tail"}``; ``returncode`` is
    ``None`` when the CLI is missing or timed out.
    """
    cmd = ["mempalace", "mine", directory, "--daemon", "--background"]
    cmd += ["--wing", wing] if wing else []
    cmd += ["--room", room] if room else []
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=MINE_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"returncode": None, "stdout_tail": "", "stderr_tail": _tail(str(exc))}
    return {"returncode": proc.returncode, "stdout_tail": _tail(proc.stdout), "stderr_tail": _tail(proc.stderr)}


def tool_mine(router, args: dict, scope: list[str]) -> dict:
    """``router_mine``: mine locally via the CLI daemon, and chunk files into a company target."""
    directory = _require_str(args, "dir")
    root = Path(directory)
    if not root.is_dir():
        raise RpcError(-32602, f"dir is not a directory: {directory}")
    company = next((n for n in scope if n != router.local_name), None)
    wing, room = args.get("wing"), args.get("room")
    wing = wing if isinstance(wing, str) and wing else None
    room = room if isinstance(room, str) and room else None
    plan = _plan_files(root, wing, room) if company else []
    local_result = mine_local(directory, wing, room)
    job_id = uuid.uuid4().hex
    by_target: dict = {router.local_name: local_result}
    out = {"job_id": job_id, "files": 0, "chunks": 0, "by_target": by_target}
    if not company:
        return out
    if local_result["returncode"] != 0:
        out["company_skipped"] = "local write failed"
        return out
    tally = {"filed": 0, "queued": 0, "partial": 0, "refused": 0}
    down = False
    for rel, file_wing, file_room, body in plan:
        out["files"] += 1
        for chunk in chunk_text(body):
            out["chunks"] += 1
            outcome = router.write_company(
                company,
                "mempalace_add_drawer",
                {"wing": file_wing, "room": file_room, "content": chunk, "source_file": rel},
                local_ref=None,
                call_id=job_id,
                mine_job_id=job_id,
                skip_send=down,
            )
            tally[outcome["status"]] += 1
            down = down or outcome["status"] == "queued"
    by_target[company] = tally
    return out
