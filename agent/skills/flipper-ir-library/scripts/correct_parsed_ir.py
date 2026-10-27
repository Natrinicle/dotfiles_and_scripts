#!/usr/bin/env python3
"""Promote Flipper raw IR to parsed NEC/NECext/Samsung32 when likelihood is high.

Usage:
  correct_parsed_ir.py PATH [--write]
  correct_parsed_ir.py --self-test

PATH is a .ir file or a directory of them. Default is dry-run. Repeat-only
NEC bursts stay raw. Command bytes are never invented unless a bundled map
uniquely matches parsed siblings. See references/parsed-ir-correct.md.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

GAP_US = 10000
NEC_MARK = 9000
NEC_SPACE = 4500
NEC_REPEAT_SPACE = 2250
NEC_BIT_MARK = 560
NEC_BIT1_SPACE = 1690
NEC_BIT0_SPACE = 560
SAMSUNG_MARK = 4500
PREAMBLE_FRAC = 0.25
BIT_FRAC = 0.30
STOP_MIN = 300
STOP_MAX = 900
TAG = "correct_parsed_ir:"

NAME_ALIASES = {
    "on": "On",
    "off": "Off",
    "power": "Power",
    "mode": "Mode",
    "auto": "Auto",
    "30m": "30m",
    "30min": "30m",
    "30 min": "30m",
    "2h": "2h",
    "2hr": "2h",
    "5h": "5h",
    "5hr": "5h",
    "10h": "10h",
    "3h": "3H",
    "3hr": "3H",
    "8h": "8H",
    "brighter": "Brighter",
    "dimmer": "Dimmer",
    "red": "Red",
    "m": "M",
    "+": "+",
    "-": "-",
}


def _near(value: int, nominal: int, frac: float) -> bool:
    slack = max(int(nominal * frac), 80)
    return abs(value - nominal) <= slack


def _norm_name(name: str) -> str:
    key = re.sub(r"\s+", " ", name.strip().lower())
    return NAME_ALIASES.get(key, name.strip())


def _hex_le(value: int, width: int = 4) -> str:
    parts = [(value >> (8 * i)) & 0xFF for i in range(width)]
    return " ".join(f"{b:02X}" for b in parts)


def _parse_hex_le(text: str) -> int:
    bytes_ = [int(p, 16) for p in text.split()]
    value = 0
    for i, byte in enumerate(bytes_):
        value |= byte << (8 * i)
    return value


def _append_byte_lsb(bits: list[int], byte: int) -> None:
    for i in range(8):
        bits.append((byte >> i) & 1)


def encode_nec(address: int, command: int, *, jitter: float = 0.0) -> list[int]:
    """32-bit NEC timings, LSB first. jitter is a signed fraction on each sample."""
    bits: list[int] = []
    _append_byte_lsb(bits, address & 0xFF)
    _append_byte_lsb(bits, (address & 0xFF) ^ 0xFF)
    _append_byte_lsb(bits, command & 0xFF)
    _append_byte_lsb(bits, (command & 0xFF) ^ 0xFF)
    timings = [NEC_MARK, NEC_SPACE]
    for bit in bits:
        timings.append(NEC_BIT_MARK)
        timings.append(NEC_BIT1_SPACE if bit else NEC_BIT0_SPACE)
    timings.append(NEC_BIT_MARK)
    if jitter:
        timings = [max(1, int(t * (1.0 + jitter))) for t in timings]
    return timings


def encode_nec_repeat(*, count: int = 3, jitter: float = 0.0) -> list[int]:
    burst = [NEC_MARK, NEC_REPEAT_SPACE, NEC_BIT_MARK]
    timings: list[int] = []
    for i in range(count):
        if i:
            timings.append(96000)
        timings.extend(burst)
    if jitter:
        timings = [max(1, int(t * (1.0 + jitter))) for t in timings]
    return timings


def split_frames(data: list[int], gap_us: int = GAP_US) -> list[list[int]]:
    """Split on long *spaces* (odd indexes). A jittered 9 ms header mark is even."""
    frames: list[list[int]] = []
    start = 0
    for i, value in enumerate(data):
        if i % 2 == 1 and value > gap_us:
            frames.append(data[start:i])
            start = i + 1
    frames.append(data[start:])
    return [f for f in frames if f]


def _bits_from_pairs(rest: list[int], nbits: int) -> tuple[list[int], list[int]] | None:
    if len(rest) < nbits * 2:
        return None
    bits: list[int] = []
    for i in range(nbits):
        mark = rest[i * 2]
        space = rest[i * 2 + 1]
        if not _near(mark, NEC_BIT_MARK, BIT_FRAC):
            return None
        if _near(space, NEC_BIT1_SPACE, BIT_FRAC):
            bits.append(1)
        elif _near(space, NEC_BIT0_SPACE, BIT_FRAC):
            bits.append(0)
        else:
            return None
    leftover = rest[nbits * 2 :]
    return bits, leftover


def _bytes_lsb(bits: list[int]) -> list[int]:
    out: list[int] = []
    for i in range(0, len(bits), 8):
        chunk = bits[i : i + 8]
        val = 0
        for j, bit in enumerate(chunk):
            val |= bit << j
        out.append(val)
    return out


def _stop_only(leftover: list[int]) -> bool:
    if not leftover:
        return True
    if len(leftover) == 1:
        return STOP_MIN <= leftover[0] <= STOP_MAX
    return False


@dataclass(frozen=True)
class ParsedHit:
    protocol: str
    address: int
    command: int
    kind: str  # payload | repeat | other


def classify_frame(frame: list[int]) -> ParsedHit | None:
    if frame and frame[0] > 20000:
        frame = frame[1:]
    if (
        len(frame) == 2
        and _near(frame[0], NEC_REPEAT_SPACE, PREAMBLE_FRAC)
        and STOP_MIN <= frame[1] <= STOP_MAX
    ):
        return ParsedHit("NEC", 0, 0, "repeat")
    if len(frame) < 3:
        return None
    mark, space = frame[0], frame[1]
    if (
        _near(mark, NEC_MARK, PREAMBLE_FRAC)
        and _near(space, NEC_REPEAT_SPACE, PREAMBLE_FRAC)
        and len(frame) <= 4
        and STOP_MIN <= frame[-1] <= STOP_MAX
    ):
        return ParsedHit("NEC", 0, 0, "repeat")
    samsung = _near(mark, SAMSUNG_MARK, PREAMBLE_FRAC) and _near(
        space, SAMSUNG_MARK, PREAMBLE_FRAC
    )
    nec_data = _near(mark, NEC_MARK, PREAMBLE_FRAC) and _near(
        space, NEC_SPACE, PREAMBLE_FRAC
    )
    if not (samsung or nec_data):
        return None
    decoded = _bits_from_pairs(frame[2:], 32)
    if decoded is None:
        return None
    bits, leftover = decoded
    if not _stop_only(leftover):
        return None
    bytes_ = _bytes_lsb(bits)
    if len(bytes_) != 4:
        return None
    a, a_inv, c, c_inv = bytes_
    cmd_ok = c == (c_inv ^ 0xFF)
    addr_ok = a == (a_inv ^ 0xFF)
    if samsung:
        if not (cmd_ok and addr_ok):
            return None
        return ParsedHit("Samsung32", a, c, "payload")
    if addr_ok and cmd_ok:
        return ParsedHit("NEC", a, c, "payload")
    if cmd_ok:
        return ParsedHit("NECext", a | (a_inv << 8), c | (c_inv << 8), "payload")
    return None


def classify_raw(data: list[int]) -> ParsedHit | None:
    payloads: list[ParsedHit] = []
    saw_repeat = False
    for frame in split_frames(data):
        hit = classify_frame(frame)
        if hit is None:
            continue
        if hit.kind == "repeat":
            saw_repeat = True
            continue
        payloads.append(hit)
    if payloads:
        first = payloads[0]
        if all(
            p.protocol == first.protocol
            and p.address == first.address
            and p.command == first.command
            for p in payloads
        ):
            return first
        return None
    if saw_repeat:
        return ParsedHit("NEC", 0, 0, "repeat")
    return None


@dataclass
class Signal:
    name: str
    comments: list[str]
    fields: dict[str, str] = field(default_factory=dict)
    data: list[int] | None = None


def parse_document(text: str) -> tuple[list[str], list[Signal]]:
    lines = text.splitlines()
    header: list[str] = []
    signals: list[Signal] = []
    pending_comments: list[str] = []
    current: Signal | None = None

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("name:"):
            if current is not None:
                signals.append(current)
            current = Signal(
                name=line.split(":", 1)[1].strip(),
                comments=pending_comments,
            )
            pending_comments = []
        elif current is None:
            header.append(line)
        elif line.startswith("data:"):
            current.data = [int(x) for x in line.split(":", 1)[1].split()]
            current.fields["data"] = line.split(":", 1)[1].strip()
        elif ":" in line and not line.startswith("#"):
            key, value = line.split(":", 1)
            current.fields[key.strip()] = value.strip()
        else:
            if current.fields or current.data is not None:
                pending_comments.append(line)
            else:
                current.comments.append(line)
        i += 1
    if current is not None:
        signals.append(current)
        if pending_comments:
            signals[-1].comments.extend(pending_comments)
    return header, signals


def _strip_tool_comments(comments: list[str]) -> list[str]:
    return [c for c in comments if TAG not in c]


def _note(comments: list[str], message: str) -> list[str]:
    cleaned = _strip_tool_comments(comments)
    tag_line = f"# {TAG} {message}"
    if cleaned and cleaned[-1].strip() == "#":
        return [*cleaned[:-1], tag_line, "#"]
    return [*cleaned, tag_line]


def render(header: list[str], signals: list[Signal]) -> str:
    out: list[str] = list(header)
    for sig in signals:
        if (
            out
            and out[-1].strip() != ""
            and not (out[-1].startswith("#") or sig.comments)
        ):
            out.append("#")
        out.extend(sig.comments)
        out.append(f"name: {sig.name}")
        order = [
            "type",
            "protocol",
            "address",
            "command",
            "frequency",
            "duty_cycle",
            "data",
        ]
        emitted = set()
        for key in order:
            if (
                key == "data"
                and sig.data is not None
                and sig.fields.get("type") == "raw"
            ):
                out.append("data: " + " ".join(str(x) for x in sig.data))
                emitted.add("data")
                continue
            if key in sig.fields and key not in emitted:
                if key == "data":
                    continue
                out.append(f"{key}: {sig.fields[key]}")
                emitted.add(key)
        for key, value in sig.fields.items():
            if key not in emitted and key != "data":
                out.append(f"{key}: {value}")
    text = "\n".join(out)
    if not text.endswith("\n"):
        text += "\n"
    return text


def load_maps(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    maps = payload.get("maps", [])
    assert isinstance(maps, list)
    return maps


def _parsed_index(
    signals: list[Signal],
) -> tuple[str | None, int | None, dict[str, int]]:
    proto: str | None = None
    addr: int | None = None
    buttons: dict[str, int] = {}
    for sig in signals:
        if sig.fields.get("type") != "parsed":
            continue
        p = sig.fields.get("protocol")
        a = _parse_hex_le(sig.fields.get("address", "00"))
        c = _parse_hex_le(sig.fields.get("command", "00"))
        if proto is None:
            proto, addr = p, a
        elif p != proto or a != addr:
            return None, None, {}
        buttons[_norm_name(sig.name)] = c & 0xFF if p == "NEC" else c
    return proto, addr, buttons


def _map_match(
    maps: list[dict[str, object]],
    protocol: str | None,
    address: int | None,
    parsed: dict[str, int],
) -> dict[str, object] | None:
    if protocol is None or address is None or not parsed:
        return None
    hits: list[dict[str, object]] = []
    addr_hex = f"{address & 0xFF:02X}" if protocol == "NEC" else f"{address:X}"
    for item in maps:
        if str(item.get("protocol", "NEC")) != protocol:
            continue
        if str(item.get("address", "")).upper() != addr_hex.upper():
            continue
        buttons = item.get("buttons")
        if not isinstance(buttons, dict):
            continue
        mapped = {_norm_name(str(k)): int(str(v), 16) for k, v in buttons.items()}
        overlap = [n for n in parsed if n in mapped]
        min_anchors = int(item.get("min_anchors") or 3)
        if len(overlap) < min_anchors:
            continue
        if any(parsed[n] != mapped[n] for n in overlap):
            continue
        hits.append(item)
    if len(hits) == 1:
        return hits[0]
    return None


def correct_signals(
    signals: list[Signal], maps: list[dict[str, object]]
) -> tuple[list[str], bool]:
    reports: list[str] = []
    mutated = False
    proto, addr, parsed = _parsed_index(signals)
    matched_map = _map_match(maps, proto, addr, parsed)

    for sig in signals:
        if sig.fields.get("type") != "raw" or not sig.data:
            continue
        hit = classify_raw(sig.data)
        if hit is not None and hit.kind == "payload":
            sig.fields = {
                "type": "parsed",
                "protocol": hit.protocol,
                "address": _hex_le(hit.address),
                "command": _hex_le(hit.command),
            }
            sig.data = None
            sig.comments = _note(
                sig.comments,
                f"decoded {hit.protocol} addr {_hex_le(hit.address)} "
                f"cmd {_hex_le(hit.command)} from raw timings",
            )
            reports.append(f"{sig.name}: raw -> {hit.protocol} {hit.command:02X}")
            mutated = True
            continue
        if hit is not None and hit.kind == "repeat":
            if matched_map is not None:
                buttons = matched_map["buttons"]
                assert isinstance(buttons, dict)
                mapped = {
                    _norm_name(str(k)): int(str(v), 16) for k, v in buttons.items()
                }
                want = mapped.get(_norm_name(sig.name))
                if want is not None and proto == "NEC" and addr is not None:
                    sig.fields = {
                        "type": "parsed",
                        "protocol": "NEC",
                        "address": _hex_le(addr),
                        "command": _hex_le(want),
                    }
                    sig.data = None
                    map_id = str(matched_map.get("id", "map"))
                    sig.comments = _note(
                        sig.comments,
                        f"map {map_id} filled NEC cmd {_hex_le(want)} "
                        f"(repeat-only capture; siblings uniquely matched)",
                    )
                    reports.append(f"{sig.name}: repeat -> map {map_id} {want:02X}")
                    mutated = True
                    continue
            sibling = (
                f" sibling {proto} addr {_hex_le(addr)}"
                if proto and addr is not None
                else ""
            )
            sig.comments = _note(
                sig.comments,
                f"NEC repeat only (no command payload).{sibling}. "
                "Re-learn for a parsed command.",
            )
            reports.append(f"{sig.name}: NEC repeat only (left raw)")
            mutated = True
            continue
        reports.append(f"{sig.name}: raw, no discrete protocol match")
    return reports, mutated


def iter_ir_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(p for p in path.rglob("*.ir") if ".git" not in p.parts)


def process_file(path: Path, maps: list[dict[str, object]], write: bool) -> int:
    original = path.read_text(encoding="utf-8", errors="replace")
    header, signals = parse_document(original)
    reports, mutated = correct_signals(signals, maps)
    new_text = render(header, signals) if mutated else original
    changed = new_text != original
    print(f"== {path}")
    if not reports:
        print("  no raw buttons")
    for line in reports:
        print(f"  {line}")
    if changed and write:
        path.write_text(new_text, encoding="utf-8")
        print("  wrote")
    elif changed:
        print("  dry-run (pass --write to apply)")
    return 0


def _self_test() -> int:
    maps = [
        {
            "id": "test-80",
            "protocol": "NEC",
            "address": "80",
            "min_anchors": 3,
            "buttons": {
                "On": "01",
                "Off": "03",
                "Mode": "05",
                "2h": "1F",
                "10h": "09",
            },
        }
    ]
    nec = encode_nec(0x80, 0x01, jitter=0.12)
    hit = classify_raw(nec)
    assert hit is not None and hit.kind == "payload"
    assert hit.protocol == "NEC" and hit.address == 0x80 and hit.command == 0x01

    repeats = encode_nec_repeat(count=4, jitter=0.05)
    hit = classify_raw(repeats)
    assert hit is not None and hit.kind == "repeat"

    # Flipper sometimes prefixes a timeout mark before the first repeat.
    bls_repeat = [
        1073705499,
        2243,
        578,
        96079,
        9170,
        2242,
        579,
        96078,
        9170,
        2243,
        577,
    ]
    hit = classify_raw(bls_repeat)
    assert hit is not None and hit.kind == "repeat"

    # 36-bit invert-middle (Carrier-class) must not become NEC.
    carrier = [8243, 4156]
    for i in range(36):
        carrier.extend([532, 1528 if i % 3 == 0 else 500])
    carrier.append(532)
    hit = classify_raw(carrier)
    assert hit is None or hit.kind != "payload"

    text = """Filetype: IR signals file
Version: 1
#
name: On
type: parsed
protocol: NEC
address: 80 00 00 00
command: 01 00 00 00
#
name: Off
type: parsed
protocol: NEC
address: 80 00 00 00
command: 03 00 00 00
#
name: 2h
type: parsed
protocol: NEC
address: 80 00 00 00
command: 1F 00 00 00
#
name: Mode
type: raw
frequency: 38000
duty_cycle: 0.330000
data: PLACEHOLDER
#
name: JitterOn
type: raw
frequency: 38000
duty_cycle: 0.330000
data: PLACEHOLDER2
"""
    text = text.replace("PLACEHOLDER2", " ".join(str(x) for x in nec))
    text = text.replace("PLACEHOLDER", " ".join(str(x) for x in repeats))
    header, signals = parse_document(text)
    reports, mutated = correct_signals(signals, maps)
    by_name = {s.name: s for s in signals}
    assert mutated
    assert by_name["JitterOn"].fields["type"] == "parsed"
    assert by_name["JitterOn"].fields["command"] == "01 00 00 00"
    assert by_name["Mode"].fields["type"] == "parsed"
    assert by_name["Mode"].fields["command"] == "05 00 00 00"
    assert any("map test-80" in r for r in reports)
    rendered = render(header, signals)
    _, signals2 = parse_document(rendered)
    assert len(signals2) == 5

    nomap_text = """Filetype: IR signals file
Version: 1
#
name: On
type: parsed
protocol: NEC
address: 80 00 00 00
command: 01 00 00 00
#
name: Off
type: parsed
protocol: NEC
address: 80 00 00 00
command: 03 00 00 00
#
name: 2h
type: parsed
protocol: NEC
address: 80 00 00 00
command: 1F 00 00 00
#
name: Mode
type: raw
frequency: 38000
duty_cycle: 0.330000
data: PLACEHOLDER
"""
    nomap_text = nomap_text.replace("PLACEHOLDER", " ".join(str(x) for x in bls_repeat))
    _, nomap_signals = parse_document(nomap_text)
    nomap_reports, nomap_mutated = correct_signals(nomap_signals, [])
    nomap_by = {s.name: s for s in nomap_signals}
    assert nomap_mutated
    assert nomap_by["Mode"].fields["type"] == "raw"
    assert any("repeat only" in r for r in nomap_reports)
    print("self-test ok")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, nargs="?", help=".ir file or directory")
    parser.add_argument("--write", action="store_true", help="rewrite files in place")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument(
        "--maps",
        type=Path,
        default=Path(__file__).resolve().parent.parent
        / "references"
        / "nec-button-maps.json",
    )
    args = parser.parse_args()
    if args.self_test:
        return _self_test()
    if args.path is None:
        parser.error("PATH is required unless --self-test")
    maps = load_maps(args.maps) if args.maps.is_file() else []
    status = 0
    for ir_path in iter_ir_files(args.path):
        status = process_file(ir_path, maps, args.write) or status
    return status


if __name__ == "__main__":
    raise SystemExit(main())
