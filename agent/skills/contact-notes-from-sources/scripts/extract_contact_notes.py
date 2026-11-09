#!/usr/bin/env python3
"""Extract postal addresses and restrained note candidates from a Voice dump.

Reads Calls/*.html. Writes a compact JSON summary. Does not talk to People.
"""

from __future__ import annotations

import argparse
import html as html_lib
import json
import re
from pathlib import Path
from typing import Any

KIND_RE = re.compile(
    r"^(.*) - (Missed|Received|Placed|Text|Voicemail) - ",
    re.IGNORECASE,
)
TEL_RE = re.compile(r"tel:\+?(\d{10,15})", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
VOLUME_RE = re.compile(r"GV Takeout|files=\d|msgs=\d", re.IGNORECASE)
CRUFT_PREFIXES = (
    "me to ",
    "me-to ",
    "voicemail from ",
    "voice mail from ",
    "missed call from ",
    "call from ",
)
STATE_ZIP = r"[A-Z]{2}\s+\d{5}(?:-\d{4})?"
STREET_WORD = (
    r"(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane|"
    r"Ct|Court|Way|Pl|Place|Cir|Circle|Hwy|Highway|Pkwy|Ter|Terrace|"
    r"Trl|Trail|Loop|Pike)"
)
US_ADDR_RE = re.compile(
    rf"\b\d{{1,6}}\s+[A-Za-z0-9.'#\-]+(?:\s+[A-Za-z0-9.'#\-]+){{0,5}}"
    rf"\s+{STREET_WORD}\.?"
    rf"(?:\s+(?:Apt|Unit|#)\s*\S+)?"
    rf"[,\s]+[A-Za-z .'-]+[,\s]+{STATE_ZIP}\b",
    re.IGNORECASE,
)
GRID_ADDR_RE = re.compile(
    rf"\b\d{{1,6}}\s+[NSEW]\s+\d{{1,6}}\s+[NSEW]\b"
    rf"[,\s]+[A-Za-z .'-]+[,\s]+{STATE_ZIP}\b",
    re.IGNORECASE,
)
NOTE_RES = (
    re.compile(r"\bfavorite color[:\s]+[A-Za-z][A-Za-z -]{1,30}", re.IGNORECASE),
    re.compile(r"\bwent to [A-Za-z0-9 .'-]{2,40} together\b", re.IGNORECASE),
    re.compile(r"\bmet at [A-Za-z0-9 .'-]{2,40}", re.IGNORECASE),
    re.compile(r"\bi live at [^\n.?]{5,80}", re.IGNORECASE),
    re.compile(r"\bmy address is [^\n.?]{5,80}", re.IGNORECASE),
    re.compile(
        r"\b(?:INFP|ENFP|INFJ|ENFJ|INTP|ENTP|INTJ|ENTJ|ISFP|ESFP|ISTP|ESTP|ISFJ|ESFJ|ISTJ|ESTJ)\b"
    ),
)
STAMP_RE = re.compile(
    r"\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}.*$",
    re.IGNORECASE,
)
SKIP_NOTE_SUBSTR = (
    "bed",
    "bathroom",
    "bath house",
    "orgy",
    "fisting",
    "edging",
    "nude",
    "nudes",
    "btw?",
)
MAX_NOTES = 3


def norm_phone(s: str) -> str:
    d = re.sub(r"\D", "", s)
    return d[-10:] if len(d) >= 10 else d


def is_cruft(name: str) -> bool:
    return name.lower().startswith(CRUFT_PREFIXES)


def clean_text(raw: str) -> str:
    t = TAG_RE.sub(" ", html_lib.unescape(raw))
    return SPACE_RE.sub(" ", t).strip()


def parse_filename(name: str) -> tuple[str, str] | None:
    m = KIND_RE.match(name)
    if not m:
        return None
    key = m.group(1).strip()
    kind = m.group(2).lower()
    if not key:
        return None
    return key, kind


def extract_addresses(text: str) -> list[str]:
    found: list[str] = []
    for rx in (US_ADDR_RE, GRID_ADDR_RE):
        for m in rx.finditer(text):
            addr = SPACE_RE.sub(" ", m.group(0)).strip(" ,")
            if addr.lower() not in {a.lower() for a in found}:
                found.append(addr)
    return found


def extract_notes(text: str) -> list[str]:
    if SSN_RE.search(text) or VOLUME_RE.search(text):
        text = SSN_RE.sub(" ", text)
        if VOLUME_RE.search(text) and not any(rx.search(text) for rx in NOTE_RES):
            return []
    found: list[str] = []
    for rx in NOTE_RES:
        for m in rx.finditer(text):
            line = STAMP_RE.sub("", SPACE_RE.sub(" ", m.group(0))).strip(" .")
            if line.endswith("?"):
                continue
            low = line.lower()
            if len(line) < 4 or len(line) > 80:
                continue
            if SSN_RE.search(line) or VOLUME_RE.search(line):
                continue
            if any(s in low for s in SKIP_NOTE_SUBSTR):
                continue
            if low.startswith(("i live at", "my address is")) and not re.search(
                r"\d", line
            ):
                continue
            if low not in {n.lower() for n in found}:
                found.append(line)
            if len(found) >= MAX_NOTES:
                return found
    return found


def scan_html(path: Path) -> dict[str, Any] | None:
    parsed = parse_filename(path.name)
    if parsed is None:
        return None
    key, kind = parsed
    if is_cruft(key):
        return None
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    body = clean_text(raw)
    phones = [norm_phone(p) for p in TEL_RE.findall(raw)]
    if key.startswith("+") or key.lstrip("+").isdigit():
        phones.insert(0, norm_phone(key))
    phones = [p for p in phones if len(p) >= 10]
    uniq_phones: list[str] = []
    for p in phones:
        if p not in uniq_phones:
            uniq_phones.append(p)
    return {
        "key": key,
        "kind": kind,
        "phones": uniq_phones,
        "addresses": extract_addresses(body),
        "notes": extract_notes(body),
    }


def merge_contact(dst: dict[str, Any], src: dict[str, Any]) -> None:
    dst["files"] = int(dst.get("files") or 0) + 1
    for p in src["phones"]:
        if p not in dst["phones"]:
            dst["phones"].append(p)
    for a in src["addresses"]:
        if a.lower() not in {x.lower() for x in dst["addresses"]}:
            dst["addresses"].append(a)
    for n in src["notes"]:
        if (
            n.lower() not in {x.lower() for x in dst["notes"]}
            and len(dst["notes"]) < MAX_NOTES
        ):
            dst["notes"].append(n)


def scan_voice_dir(voice_dir: Path) -> dict[str, Any]:
    calls = voice_dir / "Calls"
    if not calls.is_dir():
        raise SystemExit(f"missing Calls dir: {calls}")
    by_key: dict[str, dict[str, Any]] = {}
    html_n = 0
    for path in calls.iterdir():
        if path.suffix.lower() != ".html":
            continue
        html_n += 1
        rec = scan_html(path)
        if rec is None:
            continue
        dst = by_key.get(rec["key"])
        if dst is None:
            dst = {
                "key": rec["key"],
                "phones": list(rec["phones"]),
                "addresses": list(rec["addresses"]),
                "notes": list(rec["notes"]),
                "files": 0,
            }
            by_key[rec["key"]] = dst
        merge_contact(dst, rec)
    useful = [c for c in by_key.values() if c["addresses"] or c["notes"]]
    useful.sort(key=lambda c: (-len(c["addresses"]) - len(c["notes"]), c["key"]))
    return {
        "voice_dir": str(voice_dir),
        "html_n": html_n,
        "keys_n": len(by_key),
        "useful_n": len(useful),
        "contacts": useful,
    }


def self_test() -> int:
    sample = (
        "Jun 1: <cite><a class='tel' href='tel:+18015551212'><span class='fn'>"
        "Ada Example</span></a></cite>: "
        "<q>Favorite color: teal. Went to the beach together. "
        "I live at 123 Main St, Springfield, IL 62701. SSN 123-45-6789 skip me. "
        "GV Takeout Text:12 files=3</q>"
    )
    body = clean_text(sample)
    addrs = extract_addresses(body)
    notes = extract_notes(body)
    assert any("123 Main St" in a for a in addrs), addrs
    assert any("favorite color" in n.lower() for n in notes), notes
    assert any("went to" in n.lower() for n in notes), notes
    assert not any("123-45" in n for n in notes), notes
    fn = parse_filename("Ada Example - Text - 2014-06-13T14_48_30Z.html")
    assert fn == ("Ada Example", "text"), fn
    assert is_cruft("Me to Ada Example")
    print("self-test ok")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--voice-dir", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.voice_dir or not args.out:
        p.error("--voice-dir and --out are required unless --self-test")
    report = scan_voice_dir(args.voice_dir)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(args.out),
                "html_n": report["html_n"],
                "keys_n": report["keys_n"],
                "useful_n": report["useful_n"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
