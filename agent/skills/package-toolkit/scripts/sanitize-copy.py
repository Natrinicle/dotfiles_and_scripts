#!/usr/bin/env python3
"""Copy files into a toolkit package while applying path/identity sanitization.

Usage:
  sanitize-copy.py --dest DIR --map MAP.yaml FILE [FILE ...]
  sanitize-copy.py --dest DIR --from-dir SRC --relative-to SRC

Default replacements always include $HOME absolute path -> ${HOME}.
Additional replacements come from MAP.yaml:

  replacements:
    - find: "acme.com"
      replace: "{company_domain}"
  drop_substrings:  # if any match, skip packing this file
    - "BEGIN OPENSSH PRIVATE KEY"
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:  # minimal fallback
    yaml = None


def load_map(path: Path | None) -> dict:
    if path is None or not path.is_file():
        return {"replacements": [], "drop_substrings": [], "drop_globs": []}
    text = path.read_text(encoding="utf-8")
    if yaml is None:
        raise SystemExit("PyYAML required for --map (pip install pyyaml)")
    data = yaml.safe_load(text) or {}
    data.setdefault("replacements", [])
    data.setdefault("drop_substrings", [])
    data.setdefault("drop_globs", [])
    return data


def should_drop(content: str, rules: dict) -> str | None:
    for s in rules.get("drop_substrings") or []:
        if s in content:
            return f"drop_substring:{s!r}"
    return None


def sanitize_text(content: str, home: str, rules: dict) -> str:
    # Longest-first path so nested paths are handled
    if home:
        content = content.replace(home, "${HOME}")
        # Also bare ${HOME} without trailing slash variants already covered
    # Generic /home/<user> and /Users/<user> (when not already ${HOME})
    content = re.sub(r"/home/[A-Za-z0-9._-]+", "${HOME}", content)
    content = re.sub(r"/Users/[A-Za-z0-9._-]+", "${HOME}", content)

    for item in rules.get("replacements") or []:
        find = item.get("find")
        repl = item.get("replace", "")
        if not find:
            continue
        flags = re.IGNORECASE if item.get("ignore_case") else 0
        if item.get("regex"):
            content = re.sub(find, repl, content, flags=flags)
        else:
            if flags:
                content = re.sub(re.escape(find), repl, content, flags=flags)
            else:
                content = content.replace(find, repl)
    return content


def copy_one(
    src: Path,
    dest_root: Path,
    rel: Path,
    home: str,
    rules: dict,
    dry_run: bool,
) -> str:
    if not src.is_file():
        return f"skip (not file): {src}"

    raw = src.read_bytes()
    # Binary? copy as-is only if small and not secret-looking name
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        out = dest_root / rel
        if dry_run:
            return f"binary copy: {src} -> {out}"
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)
        return f"binary: {out}"

    reason = should_drop(text, rules)
    if reason:
        return f"DROPPED {src} ({reason})"

    sanitized = sanitize_text(text, home, rules)
    out = dest_root / rel
    if dry_run:
        return f"would write {out} ({len(sanitized)} bytes)"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(sanitized, encoding="utf-8")
    # preserve exec bit
    mode = src.stat().st_mode
    out.chmod(mode)
    return f"wrote {out}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dest", type=Path, required=True)
    ap.add_argument("--map", type=Path, default=None)
    ap.add_argument("--from-dir", type=Path, default=None)
    ap.add_argument("--relative-to", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("files", nargs="*", type=Path)
    args = ap.parse_args()

    rules = load_map(args.map)
    home = os.environ.get("HOME", "")
    dest: Path = args.dest.expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)

    jobs: list[tuple[Path, Path]] = []
    if args.from_dir:
        root = args.from_dir.expanduser().resolve()
        rel_base = (args.relative_to or root).expanduser().resolve()
        for p in sorted(root.rglob("*")):
            if not p.is_file():
                continue
            name = p.name
            if name.startswith(".") and name.endswith(".swp"):
                continue
            if ".sync-conflict-" in name or name.endswith("~"):
                continue
            try:
                rel = p.relative_to(rel_base)
            except ValueError:
                rel = Path(p.name)
            jobs.append((p, rel))

    for f in args.files:
        src = f.expanduser().resolve()
        jobs.append((src, Path(src.name)))

    if not jobs:
        print("No files to process", file=sys.stderr)
        return 1

    for src, rel in jobs:
        print(copy_one(src, dest, rel, home, rules, args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
