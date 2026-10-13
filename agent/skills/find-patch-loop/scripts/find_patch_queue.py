#!/usr/bin/env python3
"""Project-local find-patch queue for tester / skeptic / patcher agents.

Default file: .find-patch-queue.json in the current working directory.
Does not commit, push, or patch source trees.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

STATUSES = (
    "reported",
    "confirmed",
    "rejected",
    "patching",
    "patched",
    "verified",
    "wontfix",
    "needs-info",
)
SKEPTIC_VERDICTS = ("real", "false", "needs-info")
VERIFY_VERDICTS = ("fixed", "still-open")
SKEPTIC_FROM = ("reported", "needs-info", "rejected", "confirmed")
VERIFY_FROM = ("patching", "patched", "verified")
DEFAULT_NAME = ".find-patch-queue.json"


def default_path() -> Path:
    return Path.cwd() / DEFAULT_NAME


def die(msg: str) -> None:
    raise SystemExit(msg)


def queue_file(path: Path) -> Path:
    path = path.expanduser()
    if path.name:
        return path
    if path.is_absolute():
        die(f"{path}: queue path has no file name")
    return default_path()


def tsv_cell(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\t", "\\t")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def load(path: Path) -> dict[str, Any]:
    if path.exists() and path.is_dir():
        die(f"{path}: is a directory")
    if not path.exists():
        return {"items": []}
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        die(f"{path}: {exc}")
    except UnicodeDecodeError as exc:
        die(f"{path}: not UTF-8 ({exc})")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        die(f"{path}: invalid JSON ({exc})")
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        die(f"{path}: expected object with items[]")
    items: list[Any] = []
    seen_ids: set[str] = set()
    for i, item in enumerate(data["items"]):
        if not isinstance(item, dict):
            die(f"{path}: items[{i}] must be an object")
        bid = item.get("id")
        if isinstance(bid, str) and bid:
            if bid in seen_ids:
                die(f"{path}: duplicate id {bid}")
            seen_ids.add(bid)
        items.append(item)
    data["items"] = items
    return data


def save(path: Path, data: dict[str, Any]) -> None:
    if path.exists() and path.is_dir():
        die(f"{path}: is a directory")
    payload = json.dumps(data, indent=2, sort_keys=False) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(path)
    except OSError as exc:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        die(f"{path}: {exc}")


@contextmanager
def queue_lock(path: Path) -> Iterator[None]:
    if not path.name:
        die(f"{path}: queue path has no file name")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = path.with_name(path.name + ".lock")
        with lock_path.open("a+", encoding="utf-8") as lockf:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
            yield
    except OSError as exc:
        die(f"{path}: {exc}")


def next_id(items: list[dict[str, Any]]) -> str:
    n = 0
    max_digits = sys.get_int_max_str_digits()
    for item in items:
        raw = str(item.get("id", ""))
        if raw.startswith("BUG-"):
            try:
                suffix = raw.split("-", 1)[1]
                if max_digits and len(suffix) >= max_digits:
                    raise ValueError
                n = max(n, int(suffix))
            except ValueError:
                continue
    try:
        return f"BUG-{n + 1:03d}"
    except ValueError:
        die("cannot allocate next bug id from oversized existing id")
        return ""


def find_item(items: list[dict[str, Any]], bug_id: str) -> dict[str, Any]:
    found: dict[str, Any] | None = None
    for item in items:
        if item.get("id") == bug_id:
            if found is not None:
                die(f"duplicate id: {bug_id}")
            found = item
    if found is None:
        die(f"unknown id: {bug_id}")
        raise AssertionError
    return found


def require_text(name: str, value: str) -> str:
    text = value.strip()
    if not text:
        die(f"{name} must be non-empty")
    if name == "--title" and ("\n" in text or "\r" in text):
        die("--title must be a single line")
    return text


def cmd_init(path: Path) -> int:
    if path.exists() and path.is_dir():
        die(f"{path}: is a directory")
    with queue_lock(path):
        if path.exists():
            load(path)
            print(path)
            return 0
        save(path, {"items": []})
        print(path)
        return 0


def cmd_add(path: Path, args: argparse.Namespace) -> int:
    title = require_text("--title", args.title)
    repro = require_text("--repro", args.repro)
    evidence = [require_text("--evidence", e) for e in (args.evidence or [])]
    if not evidence:
        die("add requires at least one --evidence")
    with queue_lock(path):
        data = load(path)
        item: dict[str, Any] = {
            "id": next_id(data["items"]),
            "status": "reported",
            "title": title,
            "scope": args.scope or "",
            "repro": repro,
            "expected": args.expected or "",
            "actual": args.actual or "",
            "evidence": evidence,
            "finder": args.finder or "",
        }
        data["items"].append(item)
        save(path, data)
        print(item["id"])
        return 0


def cmd_list(path: Path, args: argparse.Namespace) -> int:
    items = load(path)["items"]
    if args.status:
        items = [i for i in items if i.get("status") == args.status]
    if not items:
        print("(empty)")
        return 0
    for item in items:
        print(
            f"{item.get('id', '?')}\t{item.get('status', '?')}\t{tsv_cell(item.get('title', ''))}"
        )
    return 0


def cmd_show(path: Path, bug_id: str) -> int:
    item = find_item(load(path)["items"], bug_id)
    json.dump(item, sys.stdout, indent=2)
    print()
    return 0


def apply_skeptic(item: dict[str, Any], verdict: str, reason: str) -> None:
    status = item.get("status", "reported")
    if status in ("patching", "patched", "verified"):
        die(
            f"{item.get('id')}: status {status}; use --verify still-open for a failed patch"
        )
    if status not in SKEPTIC_FROM:
        die(f"{item.get('id')}: cannot apply --skeptic from status {status}")
    item["skeptic"] = {"verdict": verdict, "reason": reason}
    if verdict == "false":
        item["status"] = "rejected"
    elif verdict == "needs-info":
        item["status"] = "needs-info"
    elif verdict == "real":
        item["status"] = "confirmed"


def apply_verify(item: dict[str, Any], verdict: str, evidence: str) -> None:
    status = item.get("status", "reported")
    if status == "rejected":
        die(f"{item.get('id')}: rejected; will not mark verified")
    if status not in VERIFY_FROM:
        die(
            f"{item.get('id')}: --verify requires patching/patched/verified (got {status})"
        )
    if verdict == "fixed" and not evidence.strip():
        die("--verify fixed requires --reason evidence")
    item["verify"] = {"verdict": verdict, "evidence": evidence}
    if verdict == "fixed":
        item["status"] = "verified"
    else:
        item["status"] = "confirmed"


def cmd_set(path: Path, args: argparse.Namespace) -> int:
    with queue_lock(path):
        data = load(path)
        item = find_item(data["items"], args.id)
        if args.status and args.skeptic:
            die("pass --status or --skeptic, not both")
        if args.status and args.verify:
            die("pass --status or --verify, not both")
        if args.status:
            if args.status not in STATUSES:
                die(f"status must be one of {', '.join(STATUSES)}")
            if args.status == "verified":
                die(f"{item.get('id')}: cannot set status verified; use --verify fixed")
            item["status"] = args.status
        if args.skeptic:
            apply_skeptic(item, args.skeptic, args.reason or "")
        if args.verify:
            apply_verify(item, args.verify, args.reason or "")
        if args.patcher:
            item["patcher"] = args.patcher
        save(path, data)
        print(item["id"], item.get("status"))
        return 0


def cmd_next(path: Path, args: argparse.Namespace) -> int:
    want = args.status or "confirmed"
    for item in load(path)["items"]:
        if item.get("status") == want:
            print(item["id"])
            return 0
    print("(none)")
    return 1


def run_selftest() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / DEFAULT_NAME
        ns = argparse.Namespace(
            title="repro fails",
            repro="python3 -c 'raise SystemExit(1)'",
            evidence=["exit 1"],
            scope="scripts/",
            expected="exit 0",
            actual="exit 1",
            finder="finder-1",
        )
        cmd_init(path)
        cmd_add(path, ns)
        data = load(path)
        assert data["items"][0]["id"] == "BUG-001"
        assert data["items"][0]["status"] == "reported"
        set_ns = argparse.Namespace(
            id="BUG-001",
            status=None,
            skeptic="real",
            reason="reproduced exit 1",
            verify=None,
            patcher=None,
        )
        cmd_set(path, set_ns)
        assert load(path)["items"][0]["status"] == "confirmed"
        assert cmd_next(path, argparse.Namespace(status="confirmed")) == 0

        empty = Path(tmp) / "empty.json"
        empty.write_text("", encoding="utf-8")
        try:
            load(empty)
        except SystemExit:
            pass
        else:
            raise AssertionError("empty JSON must SystemExit")

        add_empty = argparse.Namespace(
            title="",
            repro="x",
            evidence=["e"],
            scope="",
            expected="",
            actual="",
            finder="",
        )
        try:
            cmd_add(path, add_empty)
        except SystemExit:
            pass
        else:
            raise AssertionError("empty title must SystemExit")

        cmd_add(
            path,
            argparse.Namespace(
                title="second",
                repro="x",
                evidence=["e"],
                scope="",
                expected="",
                actual="",
                finder="",
            ),
        )
        cmd_set(
            path,
            argparse.Namespace(
                id="BUG-002",
                status=None,
                skeptic="real",
                reason="ok",
                verify=None,
                patcher=None,
            ),
        )
        cmd_set(
            path,
            argparse.Namespace(
                id="BUG-002",
                status="patched",
                skeptic=None,
                reason="",
                verify=None,
                patcher=None,
            ),
        )
        cmd_set(
            path,
            argparse.Namespace(
                id="BUG-002",
                status=None,
                skeptic=None,
                reason="still fails",
                verify="still-open",
                patcher=None,
            ),
        )
        assert load(path)["items"][1]["status"] == "confirmed"

        try:
            cmd_add(
                path,
                argparse.Namespace(
                    title="t",
                    repro="x",
                    evidence=[""],
                    scope="",
                    expected="",
                    actual="",
                    finder="",
                ),
            )
        except SystemExit:
            pass
        else:
            raise AssertionError("empty evidence must SystemExit")

        corrupt = Path(tmp) / "corrupt.json"
        corrupt.write_text("{", encoding="utf-8")
        try:
            cmd_init(corrupt)
        except SystemExit:
            pass
        else:
            raise AssertionError("corrupt JSON init must SystemExit")

        qdir = Path(tmp) / "as-dir"
        qdir.mkdir()
        try:
            cmd_init(qdir)
        except SystemExit:
            pass
        else:
            raise AssertionError("init on directory must SystemExit")

        try:
            cmd_set(
                path,
                argparse.Namespace(
                    id="BUG-001",
                    status=None,
                    skeptic=None,
                    reason="looks good",
                    verify="fixed",
                    patcher=None,
                ),
            )
        except SystemExit:
            pass
        else:
            raise AssertionError("verify-from-confirmed must SystemExit")

        try:
            cmd_add(
                path,
                argparse.Namespace(
                    title="line1\nline2",
                    repro="r",
                    evidence=["e"],
                    scope="",
                    expected="",
                    actual="",
                    finder="",
                ),
            )
        except SystemExit:
            pass
        else:
            raise AssertionError("newline title must SystemExit")

        print("selftest ok")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--file",
        type=Path,
        default=None,
        help=f"queue JSON (default: ./{DEFAULT_NAME})",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="create an empty queue file")
    add = sub.add_parser("add", help="file a reported bug")
    add.add_argument("--title", required=True)
    add.add_argument("--repro", required=True)
    add.add_argument("--evidence", action="append", required=True)
    add.add_argument("--scope", default="")
    add.add_argument("--expected", default="")
    add.add_argument("--actual", default="")
    add.add_argument("--finder", default="")

    lst = sub.add_parser("list", help="list ids")
    lst.add_argument("--status", choices=STATUSES)

    show = sub.add_parser("show", help="print one item as JSON")
    show.add_argument("id")

    st = sub.add_parser("set", help="update status / skeptic / verify")
    st.add_argument("id")
    st.add_argument("--status", choices=STATUSES)
    st.add_argument("--skeptic", choices=SKEPTIC_VERDICTS)
    st.add_argument("--verify", choices=VERIFY_VERDICTS)
    st.add_argument("--reason", default="")
    st.add_argument("--patcher", default="")

    nxt = sub.add_parser("next", help="print the next id at a status")
    nxt.add_argument("--status", choices=STATUSES, default="confirmed")

    sub.add_parser("selftest", help="run a tiny in-temp-dir check")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "selftest":
        return run_selftest()
    path = queue_file(args.file) if args.file is not None else default_path()
    if args.cmd == "init":
        return cmd_init(path)
    if args.cmd == "add":
        return cmd_add(path, args)
    if args.cmd == "list":
        return cmd_list(path, args)
    if args.cmd == "show":
        return cmd_show(path, args.id)
    if args.cmd == "set":
        return cmd_set(path, args)
    if args.cmd == "next":
        return cmd_next(path, args)
    die(f"unknown cmd {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
