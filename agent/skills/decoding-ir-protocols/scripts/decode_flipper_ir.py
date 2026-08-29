#!/usr/bin/env python3
"""Decode Flipper Zero raw IR into per-frame bits and hex.

Usage:
  decode_flipper_ir.py path/to/file.ir
  decode_flipper_ir.py path/to/file.ir --one-us 1000 --gap-us 10000
"""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_ir(text: str) -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = []
    cur: dict[str, object] | None = None
    for line in text.splitlines():
        if line.startswith("name:"):
            cur = {"name": line.split(":", 1)[1].strip()}
            blocks.append(cur)
        elif line.startswith("type:") and cur is not None:
            cur["type"] = line.split(":", 1)[1].strip()
        elif line.startswith("protocol:") and cur is not None:
            cur["protocol"] = line.split(":", 1)[1].strip()
        elif line.startswith("address:") and cur is not None:
            cur["address"] = line.split(":", 1)[1].strip()
        elif line.startswith("command:") and cur is not None:
            cur["command"] = line.split(":", 1)[1].strip()
        elif line.startswith("data:") and cur is not None:
            cur["data"] = [int(x) for x in line.split(":", 1)[1].split()]
    return blocks


def split_frames(data: list[int], gap_us: int) -> list[list[int]]:
    frames: list[list[int]] = []
    start = 0
    for i, value in enumerate(data):
        if value > gap_us:
            frames.append(data[start:i])
            start = i + 1
    frames.append(data[start:])
    return [f for f in frames if f]


def decode_frame(frame: list[int], one_us: int) -> dict[str, object]:
    if len(frame) < 4:
        return {
            "nbits": 0,
            "hex": "",
            "bits": "",
            "leader": frame[:2],
            "leftover": frame,
        }
    rest = frame[2:]
    bits: list[int] = []
    i = 0
    while i + 1 < len(rest):
        space = rest[i + 1]
        if space > 10000:
            break
        bits.append(1 if space > one_us else 0)
        i += 2
    leftover = rest[i:]
    parts: list[str] = []
    for j in range(0, len(bits), 8):
        chunk = bits[j : j + 8]
        val = 0
        for bit in chunk:
            val = (val << 1) | bit
        parts.append(f"{val:02X}" if len(chunk) == 8 else f"{val:X}")
    return {
        "nbits": len(bits),
        "hex": " ".join(parts),
        "bits": "".join(str(b) for b in bits),
        "leader": frame[:2],
        "leftover": leftover,
        "samples": len(frame),
    }


def invert_ok(a: str, b: str) -> bool:
    if not a or not b or len(a) != len(b):
        return False
    return all(
        (c == "1" and d == "0") or (c == "0" and d == "1")
        for c, d in zip(a, b, strict=True)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ir_file", type=Path)
    parser.add_argument(
        "--one-us", type=int, default=1000, help="space longer than this is bit 1"
    )
    parser.add_argument(
        "--gap-us", type=int, default=10000, help="split frames above this"
    )
    args = parser.parse_args()

    blocks = parse_ir(args.ir_file.read_text(encoding="utf-8", errors="replace"))
    for block in blocks:
        name = str(block["name"])
        if "data" not in block:
            extra = []
            for key in ("type", "protocol", "address", "command"):
                if key in block:
                    extra.append(f"{key}={block[key]}")
            print(f"{name:24}  parsed  {' '.join(extra)}")
            continue
        data = block["data"]
        assert isinstance(data, list)
        frames = split_frames(data, args.gap_us)
        print(f"{name:24}  rawlen={len(data):4}  nframes={len(frames)}")
        decoded = [decode_frame(fr, args.one_us) for fr in frames]
        for i, row in enumerate(decoded):
            inv = ""
            if i == 1:
                inv = f"  inv={invert_ok(str(decoded[0]['bits']), str(row['bits']))}"
            print(
                f"  F{i} nbits={row['nbits']:2} leftover={row['leftover']}  "
                f"hex={row['hex']}{inv}"
            )


if __name__ == "__main__":
    main()
