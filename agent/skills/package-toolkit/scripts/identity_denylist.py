#!/usr/bin/env python3
"""Host denylist load/compile/replace for package-toolkit (stdlib only).

Tokens live in a *host* file, never in the shareable pack. Example YAML in the
pack uses fake names only.
"""

from __future__ import annotations

import os
import re
from collections.abc import Sequence
from pathlib import Path

# Example maps and denylist templates are allowed to contain fake names.
SKIP_NAME_SUBSTR = (
    "identity-denylist.example.yaml",
    "sanitize-map.example.yaml",
)

DENYLIST_PLACEHOLDER = "{subject}"

MISSING_DENYLIST_MSG = (
    "no denylist tokens loaded. Authoring requires "
    "{AGENT_HOME}/config/identity-denylist.yaml or --denylist FILE. "
    "CI/GitHub Actions may omit the host file (email/home scan only). "
    "Use --allow-missing-denylist only for tests or CI override."
)


def in_ci() -> bool:
    return bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"))


def should_require_denylist(
    *,
    allow_missing: bool,
    require: bool | None,
) -> bool:
    if allow_missing:
        return False
    if require is not None:
        return require
    return not in_ci()


def skip_denylist_on_path(path: Path) -> bool:
    name = path.name
    rendered = str(path)
    return any(s in name or s in rendered for s in SKIP_NAME_SUBSTR)


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


def collect_tokens(paths: Sequence[Path]) -> tuple[list[str], list[str]]:
    tokens: list[str] = []
    loaded: list[str] = []
    seen: set[str] = set()
    for dpath in paths:
        got = load_denylist(dpath)
        if not got:
            continue
        loaded.append(str(dpath))
        for tok in got:
            key = tok.casefold()
            if key in seen:
                continue
            seen.add(key)
            tokens.append(tok)
    return tokens, loaded


def compile_token_re(tokens: Sequence[str]) -> re.Pattern[str] | None:
    """Longest-token-first so a full name matches before a surname fragment."""
    parts: list[str] = []
    seen: set[str] = set()
    ordered = sorted(
        (t.strip() for t in tokens if t and t.strip()),
        key=len,
        reverse=True,
    )
    for t in ordered:
        key = t.casefold()
        if key in seen:
            continue
        seen.add(key)
        parts.append(rf"\b{re.escape(t)}\b")
    if not parts:
        return None
    return re.compile("|".join(parts), re.IGNORECASE)


def replace_denylist_tokens(
    text: str, token_re: re.Pattern[str] | None
) -> tuple[str, int]:
    if token_re is None:
        return text, 0
    count = 0

    def _sub(_match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return DENYLIST_PLACEHOLDER

    return token_re.sub(_sub, text), count
