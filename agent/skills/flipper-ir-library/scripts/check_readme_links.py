#!/usr/bin/env python3
"""Fail if Markdown relative links in a pack do not resolve.

Usage: check_readme_links.py [pack_root]
Default pack root is cwd. Checks *.md; skips http(s), mailto, and #fragments-only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def iter_md(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.md") if ".git" not in p.parts)


def targets(href: str, md_file: Path) -> Path | None:
    href = href.strip()
    if href.startswith(("<", ">")):
        href = href.strip("<>").strip()
    if " " in href and not href.startswith("http"):
        # allow "path 'title'" markdown
        href = href.split()[0]
    parsed = urlparse(href)
    if parsed.scheme in {"http", "https", "mailto"}:
        return None
    path = unquote(parsed.path)
    if not path or path.startswith("#"):
        return None
    return (md_file.parent / path).resolve()


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    missing: list[str] = []
    checked = 0
    for md in iter_md(root):
        text = md.read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        text = re.sub(r"`[^`]*`", "", text)
        for match in LINK.finditer(text):
            dest = targets(match.group(1), md)
            if dest is None:
                continue
            checked += 1
            if not dest.exists():
                rel_md = md.relative_to(root)
                missing.append(f"{rel_md}: {match.group(1)} -> {dest}")
    if missing:
        print(f"{len(missing)} broken link(s) ({checked} checked):")
        print("\n".join(missing))
        return 1
    print(f"ok: {checked} relative links under {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
