#!/usr/bin/env python3
"""Retarget ~/.grok/plugins/<name> to Claude installed_plugins.json installPath.

``claude plugin update`` replaces version dirs (including the ``unknown``
placeholder) and deletes the old cache folder. Grok keeps a symlink at the
old path, then plugin hooks fail with ``its plugin folder ... is gone``.

Run from SessionStart (heal before first PreToolUse) and from
``sync-from-claude.sh``. Fail-open. Never replace a native (non-symlink) dest.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

FAIL_OPEN = (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError)


def _plugins_map(installed: dict) -> dict[str, str]:
    plugins = installed.get("plugins", installed)
    mapping: dict[str, str] = {}
    if not isinstance(plugins, dict):
        return mapping
    for full_name, installs in plugins.items():
        if (
            not isinstance(full_name, str)
            or not isinstance(installs, list)
            or not installs
        ):
            continue
        src = (
            installs[-1].get("installPath") if isinstance(installs[-1], dict) else None
        )
        if isinstance(src, str) and src:
            mapping[full_name.split("@")[0]] = src
    return mapping


def retarget(
    grok_plugins: Path,
    installed_path: Path,
) -> tuple[list[str], list[str], list[str]]:
    """Return (healed, already, skipped)."""
    healed: list[str] = []
    already: list[str] = []
    skipped: list[str] = []
    installed = json.loads(installed_path.read_text(encoding="utf-8"))
    grok_plugins.mkdir(parents=True, exist_ok=True)
    for short, src in sorted(_plugins_map(installed).items()):
        if not os.path.isdir(src):
            skipped.append(f"{short} (missing {src})")
            continue
        dest = grok_plugins / short
        if dest.exists() and not dest.is_symlink():
            skipped.append(f"{short} (native)")
            continue
        if dest.is_symlink() and os.readlink(dest) == src:
            already.append(short)
            continue
        if dest.is_symlink() or dest.exists():
            dest.unlink()
        dest.symlink_to(src)
        healed.append(short)
    marker = grok_plugins / ".synced-from-claude.txt"
    names = sorted({*already, *healed})
    marker.write_text("\n".join(names) + "\n", encoding="utf-8")
    return healed, already, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print every plugin line (sync-from-claude). SessionStart stays quiet unless healed.",
    )
    parser.add_argument(
        "--grok-plugins",
        default=str(Path.home() / ".grok" / "plugins"),
    )
    parser.add_argument(
        "--installed",
        default=str(Path.home() / ".claude" / "plugins" / "installed_plugins.json"),
    )
    args = parser.parse_args(argv)
    try:
        healed, already, skipped = retarget(
            Path(args.grok_plugins), Path(args.installed)
        )
    except FAIL_OPEN:
        return 0
    if args.verbose:
        for name in already:
            print(f"plugin: {name} (already)")
        for name in healed:
            print(f"plugin: {name}")
        for item in skipped:
            print(f"skip plugin: {item}", file=sys.stderr)
    elif healed:
        print(
            "Retargeted Grok plugin symlinks: "
            + ", ".join(healed)
            + ". Source: Claude installed_plugins.json. Restart if hooks still fail."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
