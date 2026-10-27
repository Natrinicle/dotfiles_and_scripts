#!/usr/bin/env python3
"""Fail if toolkit files contain residual personal or company identity tokens.

Hard gate before committing a shareable pack. Tokens live in a *host* denylist
(not in the public pack) plus optional repo-local gitignored files.

Usage:
  residual-identity-scan.py [--root DIR] [--denylist FILE] [FILE ...]
  residual-identity-scan.py --self-test

With no FILE arguments, walks the whole --root tree.
Authoring fails if no denylist tokens load (default unless CI/GITHUB_ACTIONS).

Exit 1 on the first hit. Prints path:line: snippet (token redacted).
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

from identity_denylist import (
    MISSING_DENYLIST_MSG,
    SKIP_NAME_SUBSTR,
    collect_tokens,
    compile_token_re,
    default_denylist_paths,
    should_require_denylist,
    skip_denylist_on_path,
)

SKIP_DIR_NAMES = {
    ".git",
    ".ruff_cache",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
}

SKIP_FILE_NAMES = {
    ".find-patch-queue.json",
    ".find-patch-queue.json.lock",
}

SKIP_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".pdf",
    ".bin",
    ".hex",
    ".pyc",
    ".so",
    ".o",
}

EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
)
HOME_RE = re.compile(r"(?:/home|/Users)/[A-Za-z0-9._-]+")

EMAIL_ALLOW_DOMAINS = {
    "example.com",
    "example.org",
    "example.net",
    "invalid",
    "localhost",
    "friendlytown.com",  # pack resume placeholder
}

# Example / container logins used in docs and docker targets.
HOME_ALLOW_LOGINS = {
    "alice",
    "bob",
    "user",
    "worker",
    "ubuntu",
    "nobody",
    "www-data",
    "debian",
    "node",
}

PLACEHOLDER_MARKERS = ("{user}", "{company_domain}", "${HOME}", "$USER")


def should_skip_file(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    if skip_denylist_on_path(path) or skip_denylist_on_path(rel):
        return True
    if path.name in SKIP_FILE_NAMES:
        return True
    if any(s in path.name or s in str(rel) for s in SKIP_NAME_SUBSTR):
        return True
    return path.suffix.lower() in SKIP_SUFFIXES


def iter_git_files(root: Path) -> list[Path] | None:
    """Tracked + untracked-not-ignored. None if this root is not a git work tree."""
    git_dir = root / ".git"
    if not git_dir.exists():
        return None
    try:
        proc = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "-z",
                "--cached",
                "--others",
                "--exclude-standard",
            ],
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    out: list[Path] = []
    for raw in proc.stdout.split(b"\0"):
        if not raw:
            continue
        rel = raw.decode("utf-8", errors="replace")
        path = root / rel
        if path.is_file():
            out.append(path)
    return out


def iter_files(root: Path, explicit: Sequence[Path]) -> Iterable[Path]:
    if explicit:
        for p in explicit:
            if p.is_file():
                yield p
        return
    git_files = iter_git_files(root)
    if git_files is not None:
        yield from git_files
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
        for fn in filenames:
            yield Path(dirpath) / fn


def email_allowed(addr: str) -> bool:
    lower = addr.lower()
    if any(m.lower() in lower for m in PLACEHOLDER_MARKERS):
        return True
    domain = lower.rsplit("@", 1)[-1]
    if domain in EMAIL_ALLOW_DOMAINS:
        return True
    return domain.endswith((".example", ".invalid"))


def redact(snippet: str, match: str) -> str:
    if not match:
        return snippet.strip()
    return snippet.replace(match, "[redacted]").strip()


def scan_text(
    text: str,
    token_re: re.Pattern[str] | None,
    *,
    check_email: bool,
    check_home: bool,
) -> list[tuple[int, str, str]]:
    """Return (lineno, kind, redacted_snippet) hits."""
    hits: list[tuple[int, str, str]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if token_re is not None:
            m = token_re.search(line)
            if m:
                hits.append((i, "denylist", redact(line, m.group(0))))
                continue
        if check_email:
            for em in EMAIL_RE.findall(line):
                if not email_allowed(em):
                    hits.append((i, "email", redact(line, em)))
                    break
        if check_home:
            for m in HOME_RE.finditer(line):
                login = m.group(0).rsplit("/", 1)[-1]
                if login.lower() in HOME_ALLOW_LOGINS:
                    continue
                if login.startswith(("{", "$")):
                    continue
                hits.append((i, "absolute-home", redact(line, m.group(0))))
                break
    return hits


def scan_paths(
    root: Path,
    files: Sequence[Path],
    token_re: re.Pattern[str] | None,
    *,
    check_email: bool = True,
    check_home: bool = True,
) -> list[str]:
    reports: list[str] = []
    for path in iter_files(root, files):
        if should_skip_file(path, root):
            continue
        try:
            data = path.read_bytes()
        except OSError as exc:
            reports.append(f"{path}:0: cannot read ({exc})")
            continue
        if b"\0" in data[:2048]:
            continue
        text = data.decode("utf-8", errors="replace")
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path
        for lineno, kind, snippet in scan_text(
            text, token_re, check_email=check_email, check_home=check_home
        ):
            reports.append(f"{rel}:{lineno}:{kind}: {snippet}")
    return reports


def self_test() -> int:
    token_re = compile_token_re(["AcmeCorpXYZ", "ExampleSubjectName"])
    assert token_re is not None
    hits = scan_text(
        "See the ExampleSubjectName account claim.\ncontact foo@example.com\n",
        token_re,
        check_email=True,
        check_home=True,
    )
    kinds = {h[1] for h in hits}
    if "denylist" not in kinds:
        print("self-test: expected denylist hit", file=sys.stderr)
        return 1
    clean = scan_text(
        "See a sample password-protection claim.\nuser@{company_domain}\n${HOME}/.config\n",
        token_re,
        check_email=True,
        check_home=True,
    )
    if clean:
        print(f"self-test: unexpected hits {clean}", file=sys.stderr)
        return 1
    example_home = "/home/" + "notareallogin"
    home_hits = scan_text(
        f"path {example_home}/.bashrc\n",
        token_re,
        check_email=True,
        check_home=True,
    )
    if not any(h[1] == "absolute-home" for h in home_hits):
        print("self-test: expected absolute-home hit", file=sys.stderr)
        return 1
    allowed_home = scan_text(
        "target=/home/worker/.config\n/home/alice/.bashrc\n",
        token_re,
        check_email=True,
        check_home=True,
    )
    if allowed_home:
        print(
            f"self-test: unexpected example-home hits {allowed_home}", file=sys.stderr
        )
        return 1
    print("self-test: ok")
    return 0


def _denylist_paths(args: argparse.Namespace, root: Path) -> list[Path]:
    paths: list[Path] = []
    if not args.no_host_denylist:
        paths.extend(default_denylist_paths(root))
    for extra in args.denylist:
        p = extra.expanduser()
        if not p.is_file():
            raise SystemExit(f"residual-identity-scan: denylist not found: {p}")
        paths.append(p)
    return paths


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None, help="Toolkit repo root")
    parser.add_argument(
        "--denylist",
        action="append",
        default=[],
        type=Path,
        help="Extra denylist YAML (repeatable)",
    )
    parser.add_argument(
        "--no-host-denylist",
        action="store_true",
        help="Do not load host/default denylist paths",
    )
    parser.add_argument(
        "--require-denylist",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Fail when no denylist tokens loaded (default: on unless CI/GITHUB_ACTIONS)",
    )
    parser.add_argument(
        "--allow-missing-denylist",
        action="store_true",
        help="Do not fail when no denylist tokens load (tests/CI override)",
    )
    parser.add_argument(
        "--no-email", action="store_true", help="Skip generic email scan"
    )
    parser.add_argument("--no-home", action="store_true", help="Skip /home /Users scan")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("files", nargs="*", type=Path)
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    root = (args.root or Path.cwd()).resolve()
    tokens, loaded = collect_tokens(_denylist_paths(args, root))
    require = should_require_denylist(
        allow_missing=args.allow_missing_denylist,
        require=args.require_denylist,
    )
    if require and not tokens:
        print(f"residual-identity-scan: FAIL: {MISSING_DENYLIST_MSG}", file=sys.stderr)
        return 1

    token_re = compile_token_re(tokens)
    files = [p if p.is_absolute() else root / p for p in args.files]

    reports = scan_paths(
        root,
        files,
        token_re,
        check_email=not args.no_email,
        check_home=not args.no_home,
    )

    if loaded:
        print(f"residual-identity-scan: denylist files ({len(tokens)} tokens):")
        for p in loaded:
            print(f"  {p}")
    else:
        print(
            "residual-identity-scan: no denylist loaded "
            "(generic email/home scan only). "
            "Set {AGENT_HOME}/config/identity-denylist.yaml on this host.",
            file=sys.stderr,
        )

    if reports:
        print("residual-identity-scan: FAIL", file=sys.stderr)
        for line in reports:
            print(line, file=sys.stderr)
        print(
            "Replace with {subject}/{account}/{company} or drop the name. "
            "Do not put denylist tokens in the shareable pack.",
            file=sys.stderr,
        )
        return 1
    print("residual-identity-scan: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
