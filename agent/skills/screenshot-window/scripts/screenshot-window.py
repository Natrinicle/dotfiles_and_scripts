#!/usr/bin/env python3
"""Capture a KWin window by title/UUID without activating it or notifying."""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_DIR = Path("/tmp/agent-screenshots")
HELPER_NAME = "kwin-screenshot2"
DESKTOP_ID = "screenshot-window.desktop"
BUS_IFACE = "org.screenshotwindow.dump"


def _skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _scripts_dir() -> Path:
    return Path(__file__).resolve().parent


def _lib_dir() -> Path:
    return Path.home() / ".local/lib/screenshot-window"


def _helper_path() -> Path:
    return _lib_dir() / HELPER_NAME


def _desktop_path() -> Path:
    return Path.home() / ".local/share/applications" / DESKTOP_ID


def _dest_dir(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser()
    env = os.environ.get("SCREENSHOT_WINDOW_DIR")
    if env:
        return Path(env).expanduser()
    return DEFAULT_DIR


def _run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=False, text=True, **kwargs)


def ensure_helper_built() -> Path:
    src = _scripts_dir() / f"{HELPER_NAME}.c"
    dest = _helper_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not src.is_file():
        raise SystemExit(f"missing source: {src}")
    need = True
    if dest.is_file():
        need = dest.stat().st_mtime < src.stat().st_mtime
    if need:
        cflags = _run(
            ["pkg-config", "--cflags", "--libs", "dbus-1", "libpng"],
            capture_output=True,
        )
        if cflags.returncode != 0:
            raise SystemExit(
                "pkg-config dbus-1 libpng failed. Install libdbus-1-dev and libpng-dev."
            )
        flags = cflags.stdout.split()
        cmd = ["gcc", "-O2", "-Wall", str(src), "-o", str(dest), *flags]
        built = _run(cmd, capture_output=True)
        if built.returncode != 0:
            sys.stderr.write(built.stderr)
            raise SystemExit("failed to compile kwin-screenshot2")
        dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return dest.resolve()


def ensure_desktop(helper: Path) -> Path:
    template = _skill_root() / "share" / "screenshot-window.desktop.in"
    if not template.is_file():
        raise SystemExit(f"missing desktop template: {template}")
    body = template.read_text(encoding="utf-8").replace("@EXEC@", str(helper))
    dest = _desktop_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.is_file() or dest.read_text(encoding="utf-8") != body:
        dest.write_text(body, encoding="utf-8")
        _run(["kbuildsycoca6"], capture_output=True)
        time.sleep(0.2)
    return dest


def doctor() -> int:
    helper = ensure_helper_built()
    desktop = ensure_desktop(helper)
    print(f"helper: {helper}")
    print(f"desktop: {desktop}")
    print(f"exec: {helper}")
    ver = _run(
        [
            "gdbus",
            "call",
            "--session",
            "--dest",
            "org.kde.KWin.ScreenShot2",
            "--object-path",
            "/org/kde/KWin/ScreenShot2",
            "--method",
            "org.freedesktop.DBus.Properties.Get",
            "org.kde.KWin.ScreenShot2",
            "Version",
        ],
        capture_output=True,
    )
    if ver.returncode == 0:
        print(f"ScreenShot2: {ver.stdout.strip()}")
    else:
        print("ScreenShot2: unreachable")
    print("ok")
    return 0


def _list_via_kwin_script() -> list[dict[str, Any]]:
    import dbus
    import dbus.service
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib

    DBusGMainLoop(set_as_default=True)
    bus_name = f"org.screenshotwindow.dump.p{os.getpid()}"
    template = (_scripts_dir() / "kwin-dump-windows.js").read_text(encoding="utf-8")
    js = template.replace("BUS_NAME_PLACEHOLDER", bus_name)

    loop = GLib.MainLoop()
    bus = dbus.SessionBus()
    name = dbus.service.BusName(bus_name, bus=bus)

    class Dump(dbus.service.Object):
        def __init__(self) -> None:
            super().__init__(bus, "/Dump")
            self.payload: str | None = None

        @dbus.service.method(BUS_IFACE, in_signature="s", out_signature="")
        def Push(self, payload: str) -> None:
            self.payload = payload
            loop.quit()

    dump = Dump()
    plugin = f"screenshot-window-dump-{os.getpid()}"
    js_path = Path(tempfile.gettempdir()) / f"{plugin}.js"
    js_path.write_text(js, encoding="utf-8")

    kwin = bus.get_object("org.kde.KWin", "/Scripting")
    scripting = dbus.Interface(kwin, "org.kde.kwin.Scripting")
    try:
        scripting.unloadScript(plugin)
    except dbus.DBusException:
        pass
    script_id = int(scripting.loadScript(str(js_path), plugin, signature="ss"))
    script = bus.get_object("org.kde.KWin", f"/Scripting/Script{script_id}")
    dbus.Interface(script, "org.kde.kwin.Script").run()

    GLib.timeout_add_seconds(5, loop.quit)
    loop.run()
    try:
        scripting.unloadScript(plugin)
    except dbus.DBusException:
        pass
    try:
        js_path.unlink()
    except OSError:
        pass
    del name
    if not dump.payload:
        raise RuntimeError("kwin dump returned no payload")
    data = json.loads(dump.payload)
    if not isinstance(data, list):
        raise TypeError("kwin dump payload is not a list")
    return data


def list_windows(*, include_skip_taskbar: bool) -> list[dict[str, Any]]:
    rows = _list_via_kwin_script()
    if include_skip_taskbar:
        return rows
    return [r for r in rows if not r.get("skipTaskbar")]


def _norm(s: str) -> str:
    return s.casefold().strip()


def match_windows(
    rows: list[dict[str, Any]],
    *,
    uuid: str | None,
    title: str | None,
    resource_class: str | None,
) -> list[dict[str, Any]]:
    hits = rows
    if uuid:
        u = uuid.strip()
        if not u.startswith("{"):
            u = "{" + u + "}"
        u = _norm(u)
        hits = [r for r in hits if _norm(str(r.get("uuid", ""))) == u]
    if title:
        needle = _norm(title)
        hits = [r for r in hits if needle in _norm(str(r.get("caption", "")))]
    if resource_class:
        needle = _norm(resource_class)
        hits = [
            r
            for r in hits
            if needle in _norm(str(r.get("resourceClass", "")))
            or needle in _norm(str(r.get("resourceName", "")))
        ]
    return hits


def _slug(text: str) -> str:
    out = []
    prev_dash = False
    for ch in text.lower():
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    slug = "".join(out).strip("-")
    return slug[:48] or "window"


def default_output(dest: Path, caption: str) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return dest / f"{_slug(caption)}-{ts}.png"


def cmd_list(args: argparse.Namespace) -> int:
    rows = list_windows(include_skip_taskbar=args.all)
    if args.json:
        json.dump(rows, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    for row in rows:
        uuid = row.get("uuid", "")
        caption = row.get("caption", "")
        klass = row.get("resourceClass", "")
        size = f"{row.get('width')}x{row.get('height')}"
        extra = []
        if row.get("minimized"):
            extra.append("minimized")
        if row.get("skipTaskbar"):
            extra.append("skipTaskbar")
        suffix = f" [{' '.join(extra)}]" if extra else ""
        print(f"{uuid}\t{klass}\t{size}\t{caption}{suffix}")
    return 0


def cmd_capture(args: argparse.Namespace) -> int:
    if not (args.uuid or args.title or args.resource_class):
        raise SystemExit("capture needs --uuid, --title, or --class")
    dest = _dest_dir(args.dir)
    if args.output:
        out = Path(args.output).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
    else:
        out = None

    helper = ensure_helper_built()
    ensure_desktop(helper)
    rows = list_windows(include_skip_taskbar=True)
    hits = match_windows(
        rows,
        uuid=args.uuid,
        title=args.title,
        resource_class=args.resource_class,
    )
    if not hits:
        raise SystemExit("no window matched")
    if len(hits) > 1:
        sys.stderr.write("ambiguous match:\n")
        for row in hits:
            sys.stderr.write(
                f"  {row.get('uuid')}\t{row.get('resourceClass')}\t{row.get('caption')}\n"
            )
        raise SystemExit(2)

    row = hits[0]
    uuid = str(row.get("uuid", ""))
    if out is None:
        out = default_output(dest, str(row.get("caption") or "window"))

    cmd = [str(helper), "--handle", uuid, "--output", str(out)]
    if args.no_decoration:
        cmd.append("--no-decoration")
    else:
        cmd.append("--decoration")
    if args.cursor:
        cmd.append("--cursor")
    else:
        cmd.append("--no-cursor")
    if args.shadow:
        cmd.append("--shadow")
    else:
        cmd.append("--no-shadow")
    proc = _run(cmd, capture_output=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        return proc.returncode
    path = proc.stdout.strip() or str(out)
    print(path)
    return 0


def _is_tmpish(path: Path) -> bool:
    resolved = path.resolve()
    return resolved == Path("/tmp") or Path("/tmp") in resolved.parents


def cmd_cleanup(args: argparse.Namespace) -> int:
    if args.path:
        target = Path(args.path).expanduser().resolve()
        if not _is_tmpish(target) and not args.force:
            raise SystemExit(
                f"refusing to delete outside /tmp without --force: {target}"
            )
        if target.is_file():
            target.unlink()
            print(f"removed {target}")
            return 0
        raise SystemExit(f"not a file: {target}")

    dest = _dest_dir(args.dir).resolve()
    if not _is_tmpish(dest) and not args.force:
        raise SystemExit(f"refusing to wipe {dest} (not under /tmp) without --force")
    if not dest.is_dir():
        print(f"nothing to clean: {dest}")
        return 0
    n = 0
    for child in dest.iterdir():
        if (
            child.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
            and child.is_file()
        ):
            child.unlink()
            n += 1
    if args.rmdir and not any(dest.iterdir()):
        dest.rmdir()
    print(f"removed {n} files from {dest}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="screenshot-window",
        description="Capture one KWin window by UUID/title without activating it.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    list_p = sub.add_parser("list", help="list windows (JSON or TSV)")
    list_p.add_argument("--json", action="store_true")
    list_p.add_argument(
        "--all", action="store_true", help="include skipTaskbar windows"
    )
    list_p.set_defaults(func=cmd_list)

    cap = sub.add_parser("capture", help="capture one matching window to /tmp")
    cap.add_argument("--uuid", help="KWin internalId")
    cap.add_argument("--title", help="case-insensitive caption substring")
    cap.add_argument(
        "--class", dest="resource_class", help="resourceClass/resourceName substring"
    )
    cap.add_argument(
        "-o", "--output", help="PNG path (default /tmp/agent-screenshots/...)"
    )
    cap.add_argument("--dir", help="directory for auto-named files")
    cap.add_argument("--no-decoration", action="store_true")
    cap.add_argument("--cursor", action="store_true")
    cap.add_argument("--shadow", action="store_true")
    cap.set_defaults(func=cmd_capture)

    clean = sub.add_parser("cleanup", help="delete PNGs under /tmp/agent-screenshots")
    clean.add_argument(
        "--dir", help="directory to wipe (must be under /tmp unless --force)"
    )
    clean.add_argument("--path", help="one file to delete")
    clean.add_argument("--force", action="store_true")
    clean.add_argument("--rmdir", action="store_true")
    clean.set_defaults(func=cmd_cleanup)

    doc = sub.add_parser(
        "doctor", help="build helper, install .desktop, check ScreenShot2"
    )
    doc.set_defaults(func=lambda _a: doctor())
    return p


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130) from None
