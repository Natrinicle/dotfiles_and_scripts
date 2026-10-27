#!/usr/bin/env python3
"""Heuristic leftover identity spans for the local subagent pass.

Vendor-locked public names (AWS, GitHub, Docker, …) are dropped here so a
small local model does not over-redact interface names.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from identity_denylist import skip_denylist_on_path

VENDOR_FILE = (
    Path(__file__).resolve().parent.parent / "references" / "vendor-locked-names.txt"
)

# Documented fakes used to explain the example denylist. Not real people.
DOCUMENTED_FAKES = frozenset(
    {
        "alice example",
        "acme corp",
        "globex",
        "globex's",
    }
)

PLACEHOLDER_RE = re.compile(
    r"\{[A-Za-z][A-Za-z0-9_]*\}|\$\{[A-Za-z][A-Za-z0-9_]*\}|\$[A-Z][A-Z0-9_]+"
)

PROPER_SEQ_RE = re.compile(r"\b(?:[A-Z][a-z]+(?:'[A-Za-z]+)?(?:\s+|$)){2,}")
PASCAL_RE = re.compile(r"\b[A-Z][a-z]+[A-Z][A-Za-z]+\b")
PASCAL_SKIP_SUFFIXES = (
    "Error",
    "Exit",
    "Warning",
    "Exception",
    "Process",
)
CORP_RE = re.compile(
    r"\b[A-Z][A-Za-z0-9.&'-]*(?:\s+[A-Z][A-Za-z0-9.&'-]*)*\s+"
    r"(?:Inc|LLC|Ltd|Corp|GmbH|AG|PLC)\b\.?"
)
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*")

ENGLISH_LEADERS = frozenset(
    {
        "a",
        "an",
        "the",
        "this",
        "that",
        "these",
        "those",
        "when",
        "where",
        "what",
        "which",
        "who",
        "why",
        "how",
        "if",
        "then",
        "else",
        "settings",
        "calling",
        "call",
        "thread",
        "archive",
        "kit",
        "spec",
        "needs",
        "package",
        "prefer",
        "lookup",
        "report",
        "incident",
        "expert",
        "compare",
        "created",
        "modified",
        "for",
        "from",
        "into",
        "onto",
        "with",
        "without",
        "after",
        "before",
        "during",
        "while",
        "until",
        "since",
        "because",
        "and",
        "or",
        "but",
        "not",
        "no",
        "yes",
        "use",
        "using",
        "used",
        "access",
        "accessing",
        "accessed",
        "see",
        "note",
        "notes",
        "keep",
        "replace",
        "run",
        "add",
        "set",
        "get",
        "put",
        "make",
        "also",
        "always",
        "never",
        "optional",
        "required",
        "default",
        "example",
        "examples",
        "vendor",
        "specific",
        "bits",
        "follow",
        "load",
        "copy",
        "copying",
        "shared",
        "color",
        "emoji",
        "font",
        "account",
        "compose",
        "custom",
        "treat",
        "native",
        "format",
        "output",
        "judge",
        "decision",
        "style",
        "writing",
        "stated",
        "ask",
        "steps",
        "analysis",
        "summary",
        "quality",
        "checks",
        "cleanup",
        "freshness",
        "routing",
        "scanning",
        "indicators",
        "likelihood",
        "heuristics",
        "maintainability",
        "review",
        "syncer",
        "pattern",
        "adversarial",
        "credential",
        "bandwidth",
        "download",
        "upstream",
        "lazy",
        "scope",
        "knowledge",
        "toolkit",
        "grade",
        "auto",
        "update",
        "named",
        "bind",
        "volumes",
        "plan",
        "critical",
        "changes",
        "store",
        "message",
        "model",
        "shareable",
        "packs",
        "scripts",
        "shell",
        "security",
        "system",
        "work",
        "check",
        "contact",
        "communication",
        "core",
        "strict",
        "agent",
        "skills",
        "scan",
        "write",
        "read",
        "open",
        "close",
        "start",
        "stop",
        "hard",
        "gate",
        "pack",
        "root",
        "host",
        "local",
        "authoring",
        "fails",
        "do",
        "does",
        "did",
        "to",
        "in",
        "on",
        "at",
        "by",
        "of",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "it",
        "its",
        "your",
        "you",
        "we",
        "our",
        "their",
        "they",
        "new",
        "old",
        "each",
        "every",
        "all",
        "any",
        "some",
        "such",
        "same",
        "other",
        "only",
        "just",
        "still",
        "already",
        "here",
        "there",
        "both",
        "either",
        "neither",
        "via",
        "per",
        "plus",
        "minus",
        "next",
        "previous",
        "first",
        "last",
        "one",
        "two",
        "three",
        "true",
        "false",
        "none",
        "null",
        "type",
        "name",
        "value",
        "file",
        "files",
        "path",
        "paths",
        "line",
        "lines",
        "step",
        "rule",
        "rules",
        "skill",
        "script",
        "code",
        "codes",
        "config",
        "readme",
        "install",
        "create",
        "delete",
        "remove",
        "test",
        "tests",
        "pass",
        "fail",
        "error",
        "warn",
        "info",
        "debug",
        "please",
        "thanks",
        "hello",
        "welcome",
        "overview",
        "introduction",
        "details",
        "reference",
        "references",
        "usage",
        "help",
        "common",
        "mistakes",
        "permanent",
        "exclusions",
        "benefits",
        "layout",
        "whats",
        "what's",
        "workflow",
        "classify",
        "confirm",
        "build",
        "inventory",
        "sanitize",
        "propose",
        "commit",
        "push",
        "vendor-specific",
        "item",
        "stays",
        "origin",
        "offer",
        "runner",
        "navigates",
    }
)


def default_vendor_path() -> Path:
    return VENDOR_FILE


def load_vendor_names(path: Path | None = None) -> set[str]:
    src = path or default_vendor_path()
    names: set[str] = set()
    if not src.is_file():
        return names
    for raw in src.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        names.add(line.casefold())
    return names


def _tokens(span: str) -> list[str]:
    return TOKEN_RE.findall(span)


def span_is_generic(span: str, vendor: set[str]) -> bool:
    folded = span.casefold().strip()
    if not folded:
        return True
    if folded in DOCUMENTED_FAKES or folded in vendor:
        return True
    if PLACEHOLDER_RE.fullmatch(span.strip()):
        return True
    if span.endswith(PASCAL_SKIP_SUFFIXES):
        return True
    tokens = _tokens(span)
    if not tokens:
        return True
    if " " in span.strip() and tokens[0].casefold() in ENGLISH_LEADERS:
        return True
    for tok in tokens:
        key = tok.casefold()
        if key in vendor or key in ENGLISH_LEADERS or key in DOCUMENTED_FAKES:
            continue
        if tok.startswith(("{", "$")):
            continue
        return False
    return True


def _placeholder_ranges(line: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in PLACEHOLDER_RE.finditer(line)]


def _inside(start: int, end: int, ranges: list[tuple[int, int]]) -> bool:
    return any(s <= start and end <= e for s, e in ranges)


def _collect_spans(line: str) -> list[str]:
    found: list[str] = []
    placeholders = _placeholder_ranges(line)
    for cre in (CORP_RE, PROPER_SEQ_RE, PASCAL_RE):
        for match in cre.finditer(line):
            if _inside(match.start(), match.end(), placeholders):
                continue
            span = match.group(0).strip()
            if span:
                found.append(span)
    return found


def extract_line_candidates(line: str, vendor: set[str]) -> list[str]:
    if line.lstrip().startswith("#"):
        return []
    if PLACEHOLDER_RE.search(line) and not CORP_RE.search(line):
        # Still scan; placeholders sit beside real names sometimes.
        pass
    out: list[str] = []
    seen: set[str] = set()
    for span in _collect_spans(line):
        key = span.casefold()
        if key in seen:
            continue
        if span_is_generic(span, vendor):
            continue
        seen.add(key)
        out.append(span)
    return out


def extract_text_candidates(text: str, vendor: set[str]) -> list[tuple[int, str, str]]:
    """Return (lineno, span, line) leftovers."""
    hits: list[tuple[int, str, str]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        for span in extract_line_candidates(line, vendor):
            hits.append((i, span, line.rstrip()))
    return hits


PROSE_SUFFIXES = frozenset({".md", ".txt", ".rst", ".yaml", ".yml", ".toml"})
PROSE_NAMES = frozenset({"readme", "skill.md", "toolkit.yaml", "toolkit.md"})


def is_prose_file(path: Path) -> bool:
    if path.suffix.lower() in PROSE_SUFFIXES:
        return True
    return path.name.casefold() in PROSE_NAMES


SUBAGENT_SKIP_NAMES = (
    "identity-subagent-prompt.md",
    "vendor-locked-names.txt",
)


def should_skip_pack_file(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    if any(s in path.name or s in str(rel) for s in SUBAGENT_SKIP_NAMES):
        return True
    return skip_denylist_on_path(path) or skip_denylist_on_path(rel)


def format_bundle(
    rows: Iterable[tuple[str, int, str, str]],
    *,
    max_hits: int = 100,
) -> str:
    lines = [
        "# Identity subagent bundle",
        "",
        "Classify each leftover span. Keep vendor-locked public names.",
        "",
    ]
    count = 0
    for rel, lineno, span, line in rows:
        count += 1
        if count > max_hits:
            lines.append(f"... truncated after {max_hits} candidates")
            break
        snippet = line.strip()
        if len(snippet) > 200:
            snippet = snippet[:197] + "..."
        lines.append(f"- `{rel}:{lineno}` span=`{span}` :: {snippet}")
    if count == 0:
        lines.append("(no heuristic candidates)")
    lines.append("")
    lines.append(f"candidate_count: {min(count, max_hits)}")
    lines.append("")
    return "\n".join(lines)
