#!/usr/bin/env python3
"""Fail if toolkit files contain residual personal or company identity tokens.

Hard gate before committing a shareable pack. Tokens live in a *host* denylist
(not in the public pack) plus optional repo-local gitignored files.

Usage:
  residual-identity-scan.py [--root DIR] [--denylist FILE] [FILE ...]
  residual-identity-scan.py --self-test

Exit 1 on the first hit. Prints path:line: snippet (token redacted).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

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

# Example maps and denylist templates are allowed to contain fake names.
SKIP_NAME_SUBSTR = (
    "identity-denylist.example.yaml",
    "sanitize-map.example.yaml",
)

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


def _parse_forbidden_yaml(text: str) -> list[str]:
    """Tiny YAML subset: `forbidden:` then `- token` lines. No PyYAML."""
    tokens: list[str] = []
    in_forbidden = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.rstrip(":") == "forbidden" or line.startswith("forbidden:"):
            in_forbidden = True
            rest = line.split(":", 1)[1].strip() if ":" in line else ""
            if rest.startswith("[") and rest.endswith("]"):
                inner = rest[1:-1].strip()
                if inner:
                    for part in inner.split(","):
                        tok = part.strip().strip("\"'")
                        if tok:
                            tokens.append(tok)
            continue
        if in_forbidden:
            if line.startswith("- "):
                tok = line[2:].strip().strip("\"'")
                if tok:
                    tokens.append(tok)
                continue
            if not line.startswith(" ") and not line.startswith("-"):
                in_forbidden = False
    return tokens


def load_denylist(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return _parse_forbidden_yaml(path.read_text(encoding="utf-8", errors="replace"))


def default_denylist_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    env = os.environ.get("IDENTITY_DENYLIST_FILE")
    if env:
        paths.append(Path(env).expanduser())
    agent_home = os.environ.get("AGENT_HOME")
    if agent_home:
        paths.append(Path(agent_home) / "config" / "identity-denylist.yaml")
    home = Path.home()
    paths.append(home / ".claude" / "config" / "identity-denylist.yaml")
    paths.append(home / ".grok" / "config" / "identity-denylist.yaml")
    paths.append(root / "config" / "identity-denylist.local.yaml")
    paths.append(root / "config" / "identity-denylist.yaml")
    # Unique, existing only
    seen: set[Path] = set()
    out: list[Path] = []
    for p in paths:
        try:
            resolved = p.resolve()
        except OSError:
            continue
        if resolved in seen or not p.is_file():
            continue
        seen.add(resolved)
        out.append(p)
    return out


def compile_token_re(tokens: Sequence[str]) -> re.Pattern[str] | None:
    parts: list[str] = []
    for tok in tokens:
        t = tok.strip()
        if not t:
            continue
        parts.append(rf"\b{re.escape(t)}\b")
    if not parts:
        return None
    return re.compile("|".join(parts), re.IGNORECASE)


def should_skip_file(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    name = path.name
    if any(s in name or s in str(rel) for s in SKIP_NAME_SUBSTR):
        return True
    return path.suffix.lower() in SKIP_SUFFIXES


def iter_files(root: Path, explicit: Sequence[Path]) -> Iterable[Path]:
    if explicit:
        for p in explicit:
            if p.is_file():
                yield p
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
        "--no-email", action="store_true", help="Skip generic email scan"
    )
    parser.add_argument("--no-home", action="store_true", help="Skip /home /Users scan")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("files", nargs="*", type=Path)
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    root = (args.root or Path.cwd()).resolve()
    denylist_files = list(default_denylist_paths(root))
    for extra in args.denylist:
        if extra.is_file():
            denylist_files.append(extra)

    tokens: list[str] = []
    loaded: list[str] = []
    for dpath in denylist_files:
        got = load_denylist(dpath)
        if got:
            tokens.extend(got)
            loaded.append(str(dpath))

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
