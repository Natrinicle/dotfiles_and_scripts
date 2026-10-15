#!/usr/bin/env python3
"""Meld-style side-by-side file comparison.

Produces aligned two-pane diffs with insert / delete / replace chunks and
intra-line highlighting. This is the visual language of GNOME Meld
(https://meldmerge.org/), not GitHub unified ``+/-`` hunks.

Usage:
  meld_style_diff.py LEFT RIGHT [--format html|text|ansi] [--out PATH] [--open]
  meld_style_diff.py --left-text OLD --right-text NEW --left-label a --right-label b
  meld_style_diff.py --from-unified [FILE|-]
  meld_style_diff.py --git [REV] [--path FILE ...]
  meld_style_diff.py --git-range A B [--path FILE ...]

YAML and JSON also get a dyff (https://github.com/homeport/dyff) report when
``dyff`` is on PATH. Source files stay Meld-only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import functools
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, replace
from difflib import SequenceMatcher
from pathlib import Path

# Meld light palette (Tango fills at reduced saturation, matching Meld 3.x).
INSERT_BG = "#d8eedc"
DELETE_BG = "#f4d6d6"
REPLACE_BG = "#d4e2f2"
INSERT_INLINE = "#8ae234"
DELETE_INLINE = "#ef9a9a"
CONFLICT_BG = "#fce94f"


@dataclass(frozen=True)
class Span:
    """Intra-line run. kind is equal, insert, or delete."""

    kind: str
    text: str


@dataclass(frozen=True)
class Row:
    """One aligned visual row. kind is equal, insert, delete, or replace."""

    kind: str
    left_no: int | None
    right_no: int | None
    left: str
    right: str
    left_spans: tuple[Span, ...]
    right_spans: tuple[Span, ...]


@dataclass(frozen=True)
class FileCompare:
    left_label: str
    right_label: str
    rows: tuple[Row, ...]
    dyff_report: str | None = None
    skipped: str | None = None


_STRUCTURED_EXTS = {".yaml", ".yml", ".json", ".jsonc"}
_YAML_KEY = re.compile(r"""^(?:- )?(?:["'][^"']+["']|[A-Za-z0-9_./-]+)\s*:""")
_DYFF_MISSING_WARNED = False


def is_structured_label(label: str) -> bool:
    """True when the path or git label looks like YAML/JSON."""
    name = label.strip()
    if ":" in name and not name.startswith(("/", ".", "~")):
        _, _, rest = name.partition(":")
        if rest:
            name = rest
    return Path(name).suffix.lower() in _STRUCTURED_EXTS


def is_structured_text(text: str) -> bool:
    """Sniff YAML or JSON. TOML, XML, and source code stay false."""
    stripped = text.lstrip("\ufeff \t\r\n")
    if not stripped:
        return False
    if stripped.startswith("{"):
        return True
    if stripped.startswith("["):
        rest = stripped[1:].lstrip()
        if not rest:
            return True
        # JSON values, not a markdown link like [See the docs](url)
        return rest[0] in '{["0123456789-tfn]'
    if stripped.startswith(("%YAML", "%TAG", "---")):
        return True
    for line in stripped.splitlines():
        token = line.strip()
        if not token or token.startswith("#"):
            continue
        if token.startswith(("%YAML", "%TAG", "---", "...")):
            return True
        return bool(_YAML_KEY.match(token))
    return False


def looks_binary(data: bytes) -> bool:
    """NUL in the first 8KiB means the file is not text."""
    return b"\x00" in data[:8192]


def should_run_dyff(
    left_label: str,
    right_label: str,
    left_text: str,
    right_text: str,
    mode: str,
) -> bool:
    """auto: both sides YAML/JSON. always/never: honor the flag."""
    if mode == "never":
        return False
    if mode == "always":
        return True
    left_ok = is_structured_label(left_label) or is_structured_text(left_text)
    right_ok = is_structured_label(right_label) or is_structured_text(right_text)
    return left_ok and right_ok


@functools.lru_cache(maxsize=1)
def find_dyff() -> str | None:
    return shutil.which("dyff")


def _warn_dyff_missing() -> None:
    global _DYFF_MISSING_WARNED
    if _DYFF_MISSING_WARNED:
        return
    _DYFF_MISSING_WARNED = True
    print(
        "dyff not on PATH; YAML/JSON compared as text. "
        "Install: go install github.com/homeport/dyff/cmd/dyff@latest",
        file=sys.stderr,
    )


def _suffix_for_label(label: str) -> str:
    lower = label.lower()
    for ext in (".yaml", ".yml", ".json", ".jsonc"):
        if lower.endswith(ext):
            return ext
    return ".yaml"


def dyff_between_texts(
    left_text: str,
    right_text: str,
    left_label: str,
    right_label: str,
    *,
    dyff_bin: str | None = None,
    timeout: float = 30.0,
) -> str | None:
    """Run ``dyff between`` on two documents. Human report, never GitHub style."""
    binary = dyff_bin if dyff_bin is not None else find_dyff()
    if not binary:
        if dyff_bin is None:
            _warn_dyff_missing()
        return None
    with tempfile.TemporaryDirectory(prefix="meld-dyff-") as tmp:
        tmp_path = Path(tmp)
        from_path = tmp_path / f"from{_suffix_for_label(left_label)}"
        to_path = tmp_path / f"to{_suffix_for_label(right_label)}"
        from_path.write_text(left_text, encoding="utf-8")
        to_path.write_text(right_text, encoding="utf-8")
        try:
            result = subprocess.run(
                [
                    binary,
                    "--color",
                    "off",
                    "between",
                    "--omit-header",
                    str(from_path),
                    str(to_path),
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if result.returncode not in (0, 1):
            return None
        out = result.stdout.strip("\n")
        return out or None


def with_dyff(
    compare: FileCompare,
    left_text: str,
    right_text: str,
    *,
    mode: str = "auto",
    dyff_bin: str | None = None,
) -> FileCompare:
    if compare.skipped:
        return compare
    if not should_run_dyff(
        compare.left_label, compare.right_label, left_text, right_text, mode
    ):
        return compare
    report = dyff_between_texts(
        left_text,
        right_text,
        compare.left_label,
        compare.right_label,
        dyff_bin=dyff_bin,
    )
    if not report:
        return compare
    return replace(compare, dyff_report=report)


def split_lines(text: str) -> list[str]:
    """Split on newlines without keeping a trailing empty line from a final NL."""
    if text == "":
        return []
    return text.splitlines()


def intra_spans(left: str, right: str) -> tuple[tuple[Span, ...], tuple[Span, ...]]:
    """Character-level insert/delete spans inside a replace pair."""
    matcher = SequenceMatcher(a=left, b=right, autojunk=False)
    left_spans: list[Span] = []
    right_spans: list[Span] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            left_spans.append(Span("equal", left[i1:i2]))
            right_spans.append(Span("equal", right[j1:j2]))
        elif tag == "delete":
            left_spans.append(Span("delete", left[i1:i2]))
        elif tag == "insert":
            right_spans.append(Span("insert", right[j1:j2]))
        else:
            left_spans.append(Span("delete", left[i1:i2]))
            right_spans.append(Span("insert", right[j1:j2]))
    return tuple(left_spans), tuple(right_spans)


def align_rows(left: Sequence[str], right: Sequence[str]) -> list[Row]:
    """Align two line lists the way Meld does: blanks pad the shorter side."""
    matcher = SequenceMatcher(a=list(left), b=list(right), autojunk=False)
    rows: list[Row] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for i, j in zip(range(i1, i2), range(j1, j2), strict=True):
                rows.append(
                    Row(
                        kind="equal",
                        left_no=i + 1,
                        right_no=j + 1,
                        left=left[i],
                        right=right[j],
                        left_spans=(Span("equal", left[i]),),
                        right_spans=(Span("equal", right[j]),),
                    )
                )
        elif tag == "delete":
            for i in range(i1, i2):
                rows.append(
                    Row(
                        kind="delete",
                        left_no=i + 1,
                        right_no=None,
                        left=left[i],
                        right="",
                        left_spans=(Span("delete", left[i]),),
                        right_spans=(),
                    )
                )
        elif tag == "insert":
            for j in range(j1, j2):
                rows.append(
                    Row(
                        kind="insert",
                        left_no=None,
                        right_no=j + 1,
                        left="",
                        right=right[j],
                        left_spans=(),
                        right_spans=(Span("insert", right[j]),),
                    )
                )
        else:
            # One replace chunk. Pad the shorter side so corresponding
            # blocks line up, instead of emitting GitHub delete-then-insert.
            height = max(i2 - i1, j2 - j1)
            for offset in range(height):
                left_i = i1 + offset
                right_j = j1 + offset
                have_left = left_i < i2
                have_right = right_j < j2
                left_text = left[left_i] if have_left else ""
                right_text = right[right_j] if have_right else ""
                if have_left and have_right:
                    left_sp, right_sp = intra_spans(left_text, right_text)
                elif have_left:
                    left_sp, right_sp = (Span("delete", left_text),), ()
                else:
                    left_sp, right_sp = (), (Span("insert", right_text),)
                rows.append(
                    Row(
                        kind="replace",
                        left_no=left_i + 1 if have_left else None,
                        right_no=right_j + 1 if have_right else None,
                        left=left_text,
                        right=right_text,
                        left_spans=left_sp,
                        right_spans=right_sp,
                    )
                )
    return rows


def compare_paths(
    left: Path,
    right: Path,
    *,
    dyff: str = "auto",
    dyff_bin: str | None = None,
) -> FileCompare:
    """Compare two files on disk."""
    left_bytes = left.read_bytes()
    right_bytes = right.read_bytes()
    if looks_binary(left_bytes) or looks_binary(right_bytes):
        print(f"skip binary: {left} vs {right}", file=sys.stderr)
        return FileCompare(
            left_label=str(left),
            right_label=str(right),
            rows=(),
            skipped="binary",
        )
    left_text = left_bytes.decode("utf-8", errors="replace")
    right_text = right_bytes.decode("utf-8", errors="replace")
    return compare_texts(
        left_text,
        right_text,
        str(left),
        str(right),
        dyff=dyff,
        dyff_bin=dyff_bin,
    )


def compare_texts(
    left_text: str,
    right_text: str,
    left_label: str,
    right_label: str,
    *,
    dyff: str = "auto",
    dyff_bin: str | None = None,
) -> FileCompare:
    """Compare two in-memory strings."""
    compare = FileCompare(
        left_label=left_label,
        right_label=right_label,
        rows=tuple(align_rows(split_lines(left_text), split_lines(right_text))),
    )
    return with_dyff(compare, left_text, right_text, mode=dyff, dyff_bin=dyff_bin)


def parse_unified_diff(
    text: str,
    *,
    dyff: str = "auto",
    dyff_bin: str | None = None,
) -> list[FileCompare]:
    """Rebuild left/right files from a GitHub-style unified diff, then align."""
    compares: list[FileCompare] = []
    left_label = "left"
    right_label = "right"
    left_lines: list[str] = []
    right_lines: list[str] = []
    in_hunk = False
    started = False

    def flush() -> None:
        nonlocal started, in_hunk, left_lines, right_lines
        if not started:
            return
        left_text = "\n".join(left_lines)
        right_text = "\n".join(right_lines)
        if left_lines:
            left_text += "\n"
        if right_lines:
            right_text += "\n"
        compare = FileCompare(
            left_label=left_label,
            right_label=right_label,
            rows=tuple(align_rows(left_lines, right_lines)),
        )
        compares.append(
            with_dyff(compare, left_text, right_text, mode=dyff, dyff_bin=dyff_bin)
        )
        left_lines = []
        right_lines = []
        in_hunk = False

    for raw in text.splitlines():
        if raw.startswith(("diff ", "index ")):
            if raw.startswith("diff "):
                flush()
                started = False
            continue
        if raw.startswith("--- "):
            flush()
            left_label = raw[4:].split("\t", 1)[0].strip()
            started = True
            in_hunk = False
            continue
        if raw.startswith("+++ "):
            right_label = raw[4:].split("\t", 1)[0].strip()
            started = True
            continue
        if raw.startswith("@@"):
            in_hunk = True
            continue
        if not in_hunk:
            continue
        if raw.startswith("\\"):
            continue
        if raw.startswith("-"):
            left_lines.append(raw[1:])
        elif raw.startswith("+"):
            right_lines.append(raw[1:])
        elif raw.startswith(" "):
            left_lines.append(raw[1:])
            right_lines.append(raw[1:])
        else:
            # Some generators omit the leading space on context lines.
            left_lines.append(raw)
            right_lines.append(raw)
    flush()
    return compares


def chunk_stats(rows: Sequence[Row]) -> dict[str, int]:
    """Count change *chunks* (contiguous kind runs), plus equal lines."""
    stats = {"insert": 0, "delete": 0, "replace": 0, "equal_lines": 0, "chunks": 0}
    prev = ""
    for row in rows:
        if row.kind == "equal":
            stats["equal_lines"] += 1
            prev = "equal"
            continue
        if row.kind != prev:
            stats["chunks"] += 1
            stats[row.kind] = stats.get(row.kind, 0) + 1
            prev = row.kind
    return stats


def _ln_width(rows: Sequence[Row]) -> int:
    nums = [n for row in rows for n in (row.left_no, row.right_no) if n is not None]
    if not nums:
        return 2
    return max(2, len(str(max(nums))))


def _marker(kind: str) -> str:
    return {"insert": "+", "delete": "-", "replace": "*", "equal": " "}.get(kind, " ")


def _truncate(text: str, width: int) -> str:
    if width <= 0:
        return ""
    if len(text) <= width:
        return text.ljust(width)
    if width == 1:
        return "…"
    return text[: width - 1] + "…"


def _side_text(row: Row, side: str, col_width: int, ln_width: int) -> str:
    number = row.left_no if side == "left" else row.right_no
    body = row.left if side == "left" else row.right
    num = f"{number:>{ln_width}}" if number is not None else " " * ln_width
    # gutter + " | " + body
    body_width = col_width - ln_width - 3
    body_width = max(body_width, 8)
    return f"{num} | {_truncate(body, body_width)}"


def _pane_width(total_width: int) -> int:
    # marker + space + left + " | " + right
    inner = max(40, total_width) - 5
    return inner // 2


def _append_dyff_block(
    lines: list[str], compare: FileCompare, *, ansi: bool = False
) -> None:
    if not compare.dyff_report:
        return
    header = "Structured diff (dyff)"
    lines.append(f"\x1b[1m{header}\x1b[0m" if ansi else header)
    lines.extend(compare.dyff_report.splitlines())
    lines.append("")


def render_text(compares: Sequence[FileCompare], width: int = 88) -> str:
    """Two-column aligned text. No ``@@`` hunks, no ``---/+++`` file headers."""
    lines: list[str] = []
    pane = _pane_width(width)
    for index, compare in enumerate(compares):
        if index:
            lines.append("")
        if compare.skipped:
            lines.append(
                f"Skipped {compare.skipped}: {compare.left_label} | {compare.right_label}"
            )
            continue
        _append_dyff_block(lines, compare)
        ln_width = _ln_width(compare.rows)
        left_head = _truncate(compare.left_label, pane)
        right_head = _truncate(compare.right_label, pane)
        lines.append(f"  {left_head} | {right_head}")
        lines.append(f"--{'-' * pane}-+-{'-' * pane}")
        if not compare.rows:
            lines.append("  (identical or empty)")
            continue
        for row in compare.rows:
            mark = _marker(row.kind)
            left = _side_text(row, "left", pane, ln_width)
            right = _side_text(row, "right", pane, ln_width)
            lines.append(f"{mark} {left} | {right}")
    return "\n".join(lines) + ("\n" if lines else "")


def _ansi_bg(kind: str) -> str:
    return {
        "insert": "\x1b[48;2;216;238;220m",
        "delete": "\x1b[48;2;244;214;214m",
        "replace": "\x1b[48;2;212;226;242m",
        "equal": "",
    }.get(kind, "")


def _ansi_inline(kind: str) -> str:
    return {
        "insert": "\x1b[48;2;138;226;52m",
        "delete": "\x1b[48;2;239;154;154m",
        "equal": "",
    }.get(kind, "")


def _ansi_side(row: Row, side: str, col_width: int, ln_width: int) -> str:
    number = row.left_no if side == "left" else row.right_no
    spans = row.left_spans if side == "left" else row.right_spans
    body = row.left if side == "left" else row.right
    num = f"{number:>{ln_width}}" if number is not None else " " * ln_width
    body_width = col_width - ln_width - 3
    body_width = max(body_width, 8)
    painted: list[str] = []
    used = 0
    reset_to_row = _ansi_bg(row.kind)
    for span in spans:
        if used >= body_width:
            break
        take = span.text[: body_width - used]
        used += len(take)
        color = _ansi_inline(span.kind)
        if color:
            painted.append(f"{color}{take}\x1b[0m{reset_to_row}")
        else:
            painted.append(take)
    if used < body_width:
        painted.append(" " * (body_width - used))
    elif len(body) > body_width:
        painted.append("…")
    return f"{num} | {''.join(painted)}"


def render_ansi(compares: Sequence[FileCompare], width: int = 88) -> str:
    """Two-column text with Meld-like background colors."""
    reset = "\x1b[0m"
    lines: list[str] = []
    pane = _pane_width(width)
    for index, compare in enumerate(compares):
        if index:
            lines.append("")
        if compare.skipped:
            lines.append(
                f"Skipped {compare.skipped}: {compare.left_label} | {compare.right_label}"
            )
            continue
        ln_width = _ln_width(compare.rows)
        _append_dyff_block(lines, compare, ansi=True)
        lines.append(f"  {compare.left_label} | {compare.right_label}")
        for row in compare.rows:
            bg = _ansi_bg(row.kind)
            mark = _marker(row.kind)
            left = _ansi_side(row, "left", pane, ln_width)
            right = _ansi_side(row, "right", pane, ln_width)
            lines.append(f"{bg}{mark} {left} | {right}{reset}")
    return "\n".join(lines) + ("\n" if lines else "")


def _spans_html(spans: Sequence[Span]) -> str:
    parts: list[str] = []
    for span in spans:
        escaped = html.escape(span.text)
        if span.kind == "equal":
            parts.append(escaped)
        else:
            parts.append(f'<span class="inline {span.kind}">{escaped}</span>')
    return "".join(parts)


def render_html(
    compares: Sequence[FileCompare],
    *,
    dark: bool = False,
    title: str = "Meld-style comparison",
) -> str:
    """Self-contained HTML that mimics Meld's two-pane file comparison."""
    theme = "dark" if dark else "light"
    sections: list[str] = []
    for compare in compares:
        if compare.skipped:
            sections.append(
                f'<section class="file">'
                f'<div class="file-head">'
                f'<div class="label">{html.escape(compare.left_label)}</div>'
                f'<div class="summary">Skipped {html.escape(compare.skipped)}</div>'
                f'<div class="label right">{html.escape(compare.right_label)}</div>'
                f"</div></section>"
            )
            continue
        stats = chunk_stats(compare.rows)
        n_changes = stats["chunks"]
        change_word = "change" if n_changes == 1 else "changes"
        summary = (
            f"{n_changes} {change_word} "
            f"({stats['insert']} insert, {stats['delete']} delete, "
            f"{stats['replace']} replace)"
        )
        body_rows: list[str] = []
        for row in compare.rows:
            left_ln = "" if row.left_no is None else str(row.left_no)
            right_ln = "" if row.right_no is None else str(row.right_no)
            left_code = _spans_html(row.left_spans) if row.left_spans else ""
            right_code = _spans_html(row.right_spans) if row.right_spans else ""
            arrow = {"insert": "▸", "delete": "◂", "replace": "◆"}.get(row.kind, "")
            body_rows.append(
                f'<div class="cell chunk {row.kind}">'
                f'<span class="ln">{html.escape(left_ln)}</span>'
                f"<code>{left_code}</code></div>"
                f'<div class="link chunk {row.kind}">{arrow}</div>'
                f'<div class="cell chunk {row.kind}">'
                f'<span class="ln">{html.escape(right_ln)}</span>'
                f"<code>{right_code}</code></div>"
                f'<div class="map-tick {row.kind}"></div>'
            )
        dyff_block = ""
        if compare.dyff_report:
            dyff_block = (
                '<section class="dyff">'
                "<h2>Structured diff (dyff)</h2>"
                f"<pre>{html.escape(compare.dyff_report)}</pre>"
                "</section>"
            )
        sections.append(
            dyff_block + f'<section class="file">'
            f'<div class="file-head">'
            f'<div class="label">{html.escape(compare.left_label)}</div>'
            f'<div class="summary">{html.escape(summary)}</div>'
            f'<div class="label right">{html.escape(compare.right_label)}</div>'
            f"</div>"
            f'<div class="grid">'
            f"{''.join(body_rows)}"
            f"</div></section>"
        )
    css = _HTML_CSS
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        f"<title>{html.escape(title)}</title>\n"
        f"<style>\n{css}\n</style>\n</head>\n"
        f'<body class="{theme}">\n'
        f"<header><h1>{html.escape(title)}</h1>"
        "<p>Side-by-side Meld-style comparison. Green insert, red delete, "
        "blue replace. Inline highlights mark the changed tokens. "
        "YAML/JSON also show a dyff path report.</p></header>\n"
        f"{''.join(sections)}\n"
        "</body>\n</html>\n"
    )


_HTML_CSS = (
    """
:root {
  --fg: #2e3436;
  --bg: #fafafa;
  --muted: #888a85;
  --gutter: #eeeeec;
  --header: #deddda;
  --insert: """
    + INSERT_BG
    + """;
  --delete: """
    + DELETE_BG
    + """;
  --replace: """
    + REPLACE_BG
    + """;
  --insert-inline: """
    + INSERT_INLINE
    + """;
  --delete-inline: """
    + DELETE_INLINE
    + """;
  --conflict: """
    + CONFLICT_BG
    + """;
  --link: #d8d8d8;
  --font: "Source Code Pro", "DejaVu Sans Mono", ui-monospace, SFMono-Regular,
          Menlo, Consolas, monospace;
}
body.dark {
  --fg: #eeeeec;
  --bg: #1e1e1e;
  --muted: #9a9a9a;
  --gutter: #2a2a2a;
  --header: #2e2e2e;
  --insert: #1e3a28;
  --delete: #3a1e1e;
  --replace: #1e2a3a;
  --insert-inline: #387038;
  --delete-inline: #703838;
  --link: #333;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: var(--bg); color: var(--fg);
  font-family: Cantarell, "Noto Sans", sans-serif; }
header { background: var(--header); padding: 0.6rem 1rem; border-bottom: 1px solid #bbb; }
header h1 { font-size: 1rem; margin: 0 0 0.25rem; font-weight: 600; }
header p { margin: 0; font-size: 0.8rem; color: var(--muted); }
.file { margin: 0.5rem 0 1.5rem; }
.file-head { display: grid; grid-template-columns: 1fr auto 1fr; gap: 0.5rem;
  padding: 0.35rem 0.6rem; background: var(--header); font-size: 0.85rem; }
.label { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.label.right { text-align: right; }
.summary { color: var(--muted); font-size: 0.75rem; }
.grid { display: grid; grid-template-columns: minmax(0,1fr) 16px minmax(0,1fr) 10px; }
.cell { display: flex; min-width: 0; font-family: var(--font); font-size: 12px;
  line-height: 1.45; }
.cell .ln { flex: 0 0 3.2rem; text-align: right; padding: 0 0.45rem 0 0.2rem;
  color: var(--muted); background: var(--gutter); user-select: none; }
.cell code { flex: 1; padding: 0 0.4rem; white-space: pre; overflow: hidden;
  font-family: inherit; }
.chunk.insert { background: var(--insert); }
.chunk.delete { background: var(--delete); }
.chunk.replace { background: var(--replace); }
.link { background: var(--link); color: var(--muted); font-size: 9px;
  display: flex; align-items: center; justify-content: center; }
.link.chunk.insert { background: var(--insert); }
.link.chunk.delete { background: var(--delete); }
.link.chunk.replace { background: var(--replace); }
.inline.insert { background: var(--insert-inline); }
.inline.delete { background: var(--delete-inline); }
.map-tick { height: 100%; min-height: 1.45em; }
.map-tick.insert { background: var(--insert); }
.map-tick.delete { background: var(--delete); }
.map-tick.replace { background: var(--replace); }
.map-tick.equal { background: transparent; }
.dyff { margin: 0.5rem 1rem 0.25rem; padding: 0.6rem 0.8rem;
  background: var(--gutter); border-left: 4px solid var(--replace); }
.dyff h2 { font-size: 0.85rem; margin: 0 0 0.4rem; font-weight: 600; }
.dyff pre { margin: 0; font-family: var(--font); font-size: 12px;
  white-space: pre-wrap; }
@media (prefers-color-scheme: dark) {
  body.light { /* keep explicit light when requested */ }
}
""".strip()
)


def _git_output(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _git_show_bytes(repo: Path, rev: str, path: str) -> bytes | None:
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"{rev}:{path}"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def compare_git(
    repo: Path,
    left_rev: str,
    right_rev: str | None,
    paths: Sequence[str],
    *,
    dyff: str = "auto",
    dyff_bin: str | None = None,
) -> list[FileCompare]:
    """Compare git revisions. ``right_rev is None`` means the worktree."""
    repo = repo.resolve()
    selected = list(paths)
    if not selected:
        diff_args = ["diff", "--name-only", "--diff-filter=ACMRD", left_rev]
        if right_rev is not None:
            diff_args.append(right_rev)
        listed = _git_output(repo, diff_args)
        if listed.returncode != 0:
            raise RuntimeError(listed.stderr.strip() or "git diff --name-only failed")
        selected = [line for line in listed.stdout.splitlines() if line]
    compares: list[FileCompare] = []
    for path in selected:
        left_raw = _git_show_bytes(repo, left_rev, path)
        left_binary = left_raw is not None and looks_binary(left_raw)
        left_text = (
            None
            if left_raw is None or left_binary
            else left_raw.decode("utf-8", errors="replace")
        )
        if right_rev is None:
            worktree = repo / path
            if worktree.is_file():
                right_raw = worktree.read_bytes()
                right_binary = looks_binary(right_raw)
                right_text = (
                    None
                    if right_binary
                    else right_raw.decode("utf-8", errors="replace")
                )
            else:
                right_binary = False
                right_text = None
            right_label = path
        else:
            right_raw = _git_show_bytes(repo, right_rev, path)
            right_binary = right_raw is not None and looks_binary(right_raw)
            right_text = (
                None
                if right_raw is None or right_binary
                else right_raw.decode("utf-8", errors="replace")
            )
            right_label = f"{right_rev}:{path}"
        if left_binary or right_binary:
            print(f"skip binary: {path}", file=sys.stderr)
            compares.append(
                FileCompare(
                    left_label=f"{left_rev}:{path}",
                    right_label=right_label,
                    rows=(),
                    skipped="binary",
                )
            )
            continue
        if left_text is None and right_text is None:
            continue
        compares.append(
            compare_texts(
                left_text or "",
                right_text or "",
                f"{left_rev}:{path}",
                right_label,
                dyff=dyff,
                dyff_bin=dyff_bin,
            )
        )
    return compares


def default_width() -> int:
    try:
        return max(72, os.get_terminal_size().columns)
    except OSError:
        return 88


def _open_path(path: Path) -> None:
    opener = "xdg-open"
    subprocess.run([opener, str(path)], check=False)


def _print_summary(compares: Sequence[FileCompare]) -> None:
    files = len(compares)
    insert = delete = replace = chunks = 0
    for compare in compares:
        stats = chunk_stats(compare.rows)
        insert += stats["insert"]
        delete += stats["delete"]
        replace += stats["replace"]
        chunks += stats["chunks"]
    dyff_n = sum(1 for compare in compares if compare.dyff_report)
    extra = f", {dyff_n} dyff report(s)" if dyff_n else ""
    print(
        f"{files} file(s), {chunks} change chunks "
        f"({insert} insert, {delete} delete, {replace} replace){extra}",
        file=sys.stderr,
    )


def _write_html(compares: Sequence[FileCompare], out: Path, dark: bool) -> Path:
    out.write_text(render_html(compares, dark=dark), encoding="utf-8")
    return out


def build_compares(args: argparse.Namespace) -> list[FileCompare]:
    dyff_mode = args.dyff
    if args.from_unified is not None:
        source = args.from_unified
        if source == "-":
            text = sys.stdin.read()
        else:
            text = Path(source).read_text(encoding="utf-8", errors="replace")
        return parse_unified_diff(text, dyff=dyff_mode)
    if args.git_range:
        return compare_git(
            Path(args.repo),
            args.git_range[0],
            args.git_range[1],
            args.path or [],
            dyff=dyff_mode,
        )
    if args.git is not None:
        return compare_git(
            Path(args.repo), args.git, None, args.path or [], dyff=dyff_mode
        )
    if args.left_text is not None or args.right_text is not None:
        if args.left_text is None or args.right_text is None:
            raise SystemExit("--left-text and --right-text are required together")
        return [
            compare_texts(
                args.left_text,
                args.right_text,
                args.left_label or "left",
                args.right_label or "right",
                dyff=dyff_mode,
            )
        ]
    if not args.left or not args.right:
        raise SystemExit(
            "LEFT and RIGHT paths are required (or use --git / --from-unified)"
        )
    compare = compare_paths(Path(args.left), Path(args.right), dyff=dyff_mode)
    if args.left_label or args.right_label:
        compare = replace(
            compare,
            left_label=args.left_label or compare.left_label,
            right_label=args.right_label or compare.right_label,
        )
    return [compare]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Meld-style side-by-side diffs (not GitHub unified output)."
    )
    parser.add_argument("left", nargs="?", help="Left / original file")
    parser.add_argument("right", nargs="?", help="Right / new file")
    parser.add_argument("--left-text", help="Original text instead of a file")
    parser.add_argument("--right-text", help="New text instead of a file")
    parser.add_argument("--left-label", help="Override left pane label")
    parser.add_argument("--right-label", help="Override right pane label")
    parser.add_argument(
        "--from-unified",
        nargs="?",
        const="-",
        metavar="FILE",
        help="Convert a unified / GitHub diff (FILE or stdin) into Meld style",
    )
    parser.add_argument(
        "--git",
        nargs="?",
        const="HEAD",
        metavar="REV",
        help="Compare REV (default HEAD) to the worktree",
    )
    parser.add_argument(
        "--git-range",
        nargs=2,
        metavar=("A", "B"),
        help="Compare two git revisions",
    )
    parser.add_argument(
        "--path", action="append", help="Limit --git to this path (repeatable)"
    )
    parser.add_argument("--repo", default=".", help="Git repo root (default: cwd)")
    parser.add_argument(
        "--format",
        choices=["html", "text", "ansi", "all"],
        default=None,
        help="Output format (default: html with --out/--open, else ansi on a TTY, else html)",
    )
    parser.add_argument("--out", type=Path, help="Write HTML (or text) to this path")
    parser.add_argument(
        "--open", action="store_true", help="Open the HTML in the default browser"
    )
    parser.add_argument("--dark", action="store_true", help="Force dark HTML theme")
    parser.add_argument("--width", type=int, default=0, help="Text/ANSI column width")
    parser.add_argument(
        "--dyff",
        choices=["auto", "always", "never"],
        default="auto",
        help="Run dyff on YAML/JSON (auto), force, or skip. Never uses GitHub style.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    compares = build_compares(args)
    if not compares:
        print("No files to compare", file=sys.stderr)
        return 1
    _print_summary(compares)
    width = args.width or default_width()
    fmt = args.format
    if fmt is None:
        if args.out or args.open:
            fmt = "html"
        elif sys.stdout.isatty():
            fmt = "ansi"
        else:
            fmt = "html"
    html_path: Path | None = None
    if fmt in {"html", "all"}:
        if args.out and str(args.out).endswith((".txt", ".ansi")):
            html_path = args.out.with_suffix(".html")
        elif args.out:
            html_path = args.out
        else:
            stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
            html_path = Path(tempfile.gettempdir()) / f"meld-style-diff-{stamp}.html"
        _write_html(compares, html_path, dark=args.dark)
        print(str(html_path))
        if args.open:
            _open_path(html_path)
    if fmt in {"text", "all"}:
        text = render_text(compares, width=width)
        if args.out and fmt == "text":
            args.out.write_text(text, encoding="utf-8")
            print(str(args.out))
        else:
            sys.stdout.write(text if text.endswith("\n") else text + "\n")
    if fmt == "ansi":
        sys.stdout.write(render_ansi(compares, width=width))
    return 0


if __name__ == "__main__":
    sys.exit(main())
