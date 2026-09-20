#!/usr/bin/env python3
"""Classify a compiled artifact and point at likely protocol sources.

Does not run jadx or Ghidra. Prints kind, SHA-256, and a short next-step
so you do not jadx a uni-app before reading app-service.js.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import re
import sys
import zipfile
from pathlib import Path

UUID_RE = re.compile(
    rb"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
INTERESTING = (
    b"writeBLE",
    b"createBLE",
    b"181a",
    b"181A",
    b"ffe0",
    b"FFE0",
    b"fff0",
    b"FFF0",
    b"uart",
    b"UART",
    b"i2c",
    b"I2C",
    b"okhttp",
    b"http://",
    b"https://",
    b"uni.request",
    b"BluetoothGatt",
    b"Serial1",
    b"Wire.begin",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def zip_names(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as zf:
        return zf.namelist()


def zip_member_bytes(path: Path, name: str, limit: int = 2_000_000) -> bytes:
    with zipfile.ZipFile(path) as zf, zf.open(name) as fh:
        return fh.read(limit)


def scan_bytes(blob: bytes, label: str) -> None:
    hits = [pat.decode("ascii", "replace") for pat in INTERESTING if pat in blob]
    uuids = {m.group(0).decode("ascii").lower() for m in UUID_RE.finditer(blob)}
    if hits:
        print(f"  strings in {label}: {', '.join(hits[:12])}")
    if uuids:
        shown = sorted(uuids)[:8]
        print(f"  uuids in {label}: {', '.join(shown)}")


def classify_apk_tree(names: list[str]) -> str:
    joined = "\n".join(names)
    if "assets/apps/__UNI__" in joined or any(
        n.startswith("assets/apps/__UNI__") for n in names
    ):
        return "uni-app"
    if any(n.endswith(("libflutter.so", "libapp.so")) for n in names):
        return "flutter"
    if "AndroidManifest.xml" in names or any(n.endswith("classes.dex") for n in names):
        return "android-apk"
    return "zip"


def inspect_apk(path: Path, indent: str = "") -> None:
    names = zip_names(path)
    kind = classify_apk_tree(names)
    print(f"{indent}kind: {kind}")
    uni = [n for n in names if n.endswith("app-service.js") and "/www/" in n]
    for n in uni:
        print(f"{indent}js: {n} ({path.stat().st_size} bytes on disk for container)")
        print(
            f"{indent}next: grep that JS for writeBLE / uni.request / CRC; skip jadx until native .so framing is required"
        )
        try:
            scan_bytes(zip_member_bytes(path, n), n)
        except (KeyError, zipfile.BadZipFile, OSError) as exc:
            print(f"{indent}warn: could not read {n}: {exc}")
    if kind == "flutter":
        print(f"{indent}next: protocol is likely in libapp.so, not DEX")
    if kind == "android-apk" and not uni:
        print(f"{indent}next: jadx the DEX; also strings lib/*.so")
    for n in names:
        if n.endswith((".dex", ".so")):
            try:
                scan_bytes(zip_member_bytes(path, n), n)
            except (KeyError, zipfile.BadZipFile, OSError):
                pass


def inspect_xapk(path: Path) -> None:
    names = zip_names(path)
    print("kind: android-xapk")
    apks = [n for n in names if n.endswith(".apk")]
    for n in apks:
        print(f"split: {n}")
    base = next(
        (n for n in apks if "config." not in Path(n).name), apks[0] if apks else None
    )
    if not base:
        print("next: no apk members")
        return
    print(f"base: {base}")
    data = zip_member_bytes(path, base, limit=80_000_000)
    inspect_apk_from_bytes(data, prefix="  ")


def inspect_apk_from_bytes(data: bytes, prefix: str) -> None:
    bio = io.BytesIO(data)
    with zipfile.ZipFile(bio) as zf:
        names = zf.namelist()
    kind = classify_apk_tree(names)
    print(f"{prefix}kind: {kind}")
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for n in names:
            if n.endswith("app-service.js") and "/www/" in n:
                info = zf.getinfo(n)
                print(f"{prefix}js: {n} ({info.file_size} bytes)")
                print(f"{prefix}next: grep that JS; do not jadx first")
                scan_bytes(zf.read(n), n)
            if n.endswith((".dex", ".so")):
                blob = zf.read(n)
                scan_bytes(blob[:2_000_000], n)


def inspect_generic_zip(path: Path) -> None:
    names = zip_names(path)
    if any(
        n.startswith("Payload/") and n.endswith(".app/") or "/Payload/" in n
        for n in names
    ):
        print("kind: ipa")
        print("next: inspect Payload/*.app the same way as an APK (bundle vs native)")
        return
    if "AndroidManifest.xml" in names or any(n.endswith(".apk") for n in names):
        if any(n.endswith(".apk") for n in names):
            inspect_xapk(path)
        else:
            inspect_apk(path)
        return
    print("kind: zip")
    print(f"members: {len(names)}")


def inspect_blob(path: Path) -> None:
    head = path.read_bytes()[:16]
    if head[:4] == b"\x7fELF":
        print("kind: elf")
        print("next: strings + readelf; Ghidra if you need the packer")
    elif head[:2] == b"MZ":
        print("kind: pe")
        print("next: strings; Ghidra/r2 for the packer")
    elif head[:2] == b"PK":
        inspect_generic_zip(path)
        return
    else:
        print("kind: firmware-or-unknown")
        print("next: file(1), strings, binwalk; identify ISA before Ghidra")
    scan_bytes(path.read_bytes()[:4_000_000], path.name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    path: Path = args.path
    if not path.is_file():
        print(f"not a file: {path}", file=sys.stderr)
        return 1
    print(f"path: {path}")
    print(f"size: {path.stat().st_size}")
    print(f"sha256: {sha256(path)}")
    inspect_blob(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
