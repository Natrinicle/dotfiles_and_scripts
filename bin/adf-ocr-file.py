#!/usr/bin/env python3
"""File-and-route for ADF-OCR: duplex-aware split, OCR, classify, PDF metadata, local ICS."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore[misc, assignment]

DOC_TYPES = (
    "receipt",
    "bill",
    "statement",
    "tax",
    "insurance",
    "medical",
    "legal",
    "id",
    "correspondence",
    "manual",
    "other",
)
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATE_ISO_FIND = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
DATE_US = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b")
DATE_LONG = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|"
    r"october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|"
    r"oct|nov|dec)\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b",
    re.IGNORECASE,
)
DUE_CUE = re.compile(
    r"(?:pay(?:ment)?\s+due(?:\s+(?:date|by))?|due\s+(?:date|by)|pay\s+by|"
    r"please pay by|must be received(?:\s+by)?)",
    re.IGNORECASE,
)
STATEMENT_CUE = re.compile(
    r"(?:statement\s+date|period\s+ending|ending\s+date|as of|"
    r"statement\s+period|date\s+prepared)",
    re.IGNORECASE,
)
AMOUNT_CUE = re.compile(
    r"(?:amount\s+due|total\s+due|balance\s+due|please\s+pay(?:\s+this\s+amount)?|"
    r"pay\s+this\s+amount|new\s+balance)\s*[:\s]*\$?\s*"
    r"([0-9]{1,3}(?:,[0-9]{3})*\.\d{2})",
    re.IGNORECASE,
)
LETTERHEAD = re.compile(
    r"\b(?:bank|credit union|insurance|department of|county of|"
    r"llc|inc\.?|hospital|university|financial|holdings)\b",
    re.IGNORECASE,
)
PAGE_OF = re.compile(r"\bpage\s+(\d+)\s+of\s+(\d+)\b", re.IGNORECASE)
SAFE_NAME = re.compile(r"[^A-Za-z0-9 ._()-]+")
CONTINUATION = re.compile(
    r"\b(?:page\s+[2-9]\d*(?:\s+of\s+\d+)?|continued|cont['’]?d|see reverse)\b",
    re.IGNORECASE,
)
NEW_DOC_START = re.compile(r"\bpage\s+1(?:\s+of\s+\d+)?\b", re.IGNORECASE)
MONTH_NUM = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}
DOC_TYPE_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "statement",
        (
            "account statement",
            "statement period",
            "ending balance",
            "previous balance",
            "statement date",
        ),
    ),
    (
        "bill",
        (
            "amount due",
            "payment due",
            "please pay",
            "pay this amount",
            "utility bill",
            "total due",
        ),
    ),
    (
        "receipt",
        (
            "receipt",
            "amount paid",
            "payment received",
            "thank you for your payment",
        ),
    ),
    (
        "tax",
        (
            "form 1099",
            "form w-2",
            "form 1098",
            "tax document",
            "internal revenue",
        ),
    ),
    (
        "insurance",
        ("policy number", "declaration page", "coverage", "premium"),
    ),
    (
        "medical",
        ("patient", "provider", "npi", "hipaa", "explanation of benefits"),
    ),
    (
        "legal",
        ("summons", "court", "case number", "attorney", "plaintiff"),
    ),
    ("id", ("driver license", "identification card", "passport")),
    ("manual", ("user guide", "instruction manual", "quick start")),
    (
        "correspondence",
        ("dear ", "sincerely", "to whom it may concern"),
    ),
)
WORD = re.compile(r"[A-Za-z][A-Za-z']{3,}")
IMB_HUMAN = re.compile(r"\b[A-Z0-9]{6,12}[ \-]\d{3,5}[ \-]\d{5,7}\b")
ACCOUNT = re.compile(
    r"(?:account(?:\s+number)?|acct\.?|member(?:ship)?(?:\s+(?:id|number))?)"
    r"\s*[:#]?\s*([0-9]{6,12})",
    re.IGNORECASE,
)
INVOICE = re.compile(
    r"(?:invoice|statement|claim|case|policy)\s*(?:no\.?|number|#)\s*[:#]?\s*"
    r"([A-Z0-9\-]{5,})",
    re.IGNORECASE,
)
STOP = frozenset(
    [
        "this",
        "that",
        "with",
        "from",
        "your",
        "have",
        "been",
        "were",
        "they",
        "them",
        "then",
        "than",
        "also",
        "only",
        "into",
        "over",
        "after",
        "before",
        "about",
        "which",
        "their",
        "there",
        "these",
        "those",
        "would",
        "could",
        "should",
        "page",
        "pages",
        "date",
        "number",
        "account",
        "statement",
        "please",
        "contact",
        "information",
        "total",
        "amount",
        "balance",
        "payment",
        "document",
        "letter",
        "mail",
        "form",
        "continued",
        "reverse",
        "other",
    ]
)


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def env_flag(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def run(
    cmd: list[str], *, timeout: int = 60, check: bool = False
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, check=check, capture_output=True, text=True, timeout=timeout
    )


def is_blank_page(
    path: Path,
    *,
    margin: int = 80,
    blur: int = 12,
    fuzz: str = "20%",
    min_width: int = 120,
    min_height: int = 80,
) -> bool:
    convert = shutil.which("convert") or shutil.which("magick")
    if convert is None:
        return False
    cmd = [convert]
    if Path(convert).name == "magick":
        cmd.append("convert")
    cmd.extend(
        [
            str(path),
            "-shave",
            f"{margin}x{margin}",
            "-virtual-pixel",
            "White",
            "-blur",
            f"0x{blur}",
            "-fuzz",
            fuzz,
            "-trim",
            "-format",
            "%wx%h",
            "info:",
        ]
    )
    try:
        proc = run(cmd, timeout=30)
    except (subprocess.TimeoutExpired, OSError):
        return False
    if proc.returncode != 0 or "x" not in proc.stdout:
        return False
    width_s, height_s = proc.stdout.strip().split("x", 1)
    try:
        width, height = int(width_s), int(height_s)
    except ValueError:
        return False
    return width < min_width or height < min_height


def group_pages(
    pages: list[Path],
    is_blank: Callable[[Path], bool],
    *,
    duplex: bool = True,
) -> list[list[Path]]:
    """Split an ADF stack into documents.

    Duplex (scanimage ADF Duplex order is front, back, front, back):
    a blank even page is the reverse of a single-sided sheet — drop it, do
    not split. A fully blank sheet (front and back) is a separator.
    Simplex: a blank between content pages still splits.
    """
    if duplex:
        return _group_duplex(pages, is_blank)
    return _group_simplex(pages, is_blank)


def _group_simplex(
    pages: list[Path], is_blank: Callable[[Path], bool]
) -> list[list[Path]]:
    groups: list[list[Path]] = []
    current: list[Path] = []
    for page in pages:
        if is_blank(page):
            if current:
                eprint(f"   split on blank page {page.name}")
                groups.append(current)
                current = []
            continue
        current.append(page)
    if current:
        groups.append(current)
    return groups


def _group_duplex(
    pages: list[Path], is_blank: Callable[[Path], bool]
) -> list[list[Path]]:
    groups: list[list[Path]] = []
    current: list[Path] = []
    i = 0
    n = len(pages)
    while i < n:
        front = pages[i]
        back = pages[i + 1] if i + 1 < n else None
        front_blank = is_blank(front)
        back_blank = True if back is None else is_blank(back)
        if front_blank and back_blank:
            if current:
                eprint(f"   split on blank sheet {front.name}")
                groups.append(current)
                current = []
            i += 2 if back is not None else 1
            continue
        if not front_blank:
            current.append(front)
        elif back is not None:
            eprint(f"   blank front {front.name}, keep back {back.name}")
        if back is not None and not back_blank:
            current.append(back)
        elif back is not None and back_blank:
            eprint(f"   drop blank back {back.name}")
        i += 2 if back is not None else 1
    if current:
        groups.append(current)
    return groups


def sheet_fronts(pages: list[Path], *, duplex: bool) -> set[Path]:
    if not duplex:
        return set(pages)
    return {page for index, page in enumerate(pages) if index % 2 == 0}


def tesseract_text(path: Path) -> str:
    binary = shutil.which("tesseract")
    if binary is None:
        return ""
    try:
        proc = run([binary, str(path), "stdout", "--psm", "6"], timeout=60)
    except (subprocess.TimeoutExpired, OSError):
        return ""
    return proc.stdout if proc.returncode == 0 else ""


def memo_tesseract() -> Callable[[Path], str]:
    cache: dict[Path, str] = {}

    def text_of(path: Path) -> str:
        if path not in cache:
            cache[path] = tesseract_text(path)
        return cache[path]

    return text_of


@dataclass(frozen=True)
class PageSignals:
    path: Path
    text: str
    dhash: int
    barcodes: tuple[str, ...]
    identity: frozenset[str]
    tokens: frozenset[str]


def hamming64(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def dhash_int(path: Path, size: int = 8) -> int:
    if not path.is_file():
        return 0
    if Image is not None:
        try:
            image = (
                Image.open(path).convert("L").resize((size + 1, size), Image.BILINEAR)
            )
            pixels = image.load()
            bits = 0
            for row in range(size):
                for col in range(size):
                    bits = (bits << 1) | int(pixels[col, row] > pixels[col + 1, row])
            return bits
        except OSError:
            pass
    convert = shutil.which("convert") or shutil.which("magick")
    if convert is None:
        return 0
    cmd = [convert]
    if Path(convert).name == "magick":
        cmd.append("convert")
    cmd.extend(
        [
            str(path),
            "-colorspace",
            "gray",
            "-resize",
            f"{size + 1}x{size}!",
            "gray:-",
        ]
    )
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=30, check=False)
    except (subprocess.TimeoutExpired, OSError):
        return 0
    data = proc.stdout
    width = size + 1
    if len(data) < width * size:
        return 0
    bits = 0
    for row in range(size):
        for col in range(size):
            left = data[row * width + col]
            right = data[row * width + col + 1]
            bits = (bits << 1) | int(left > right)
    return bits


def usable_barcode(raw: str) -> bool:
    value = raw.strip()
    if len(value) < 8:
        return False
    return not (re.fullmatch(r"[\d+\-]+", value) and len(value) < 12)


def zbar_barcodes(path: Path) -> tuple[str, ...]:
    binary = shutil.which("zbarimg")
    if binary is None or not path.is_file():
        return ()
    try:
        proc = run([binary, "--quiet", "--raw", str(path)], timeout=20)
    except (subprocess.TimeoutExpired, OSError):
        return ()
    found: list[str] = []
    for line in proc.stdout.splitlines():
        item = line.strip()
        if usable_barcode(item) and item not in found:
            found.append(item)
    return tuple(found)


def distinctive_tokens(text: str) -> frozenset[str]:
    return frozenset(
        word.lower() for word in WORD.findall(text) if word.lower() not in STOP
    )


def identity_keys(text: str, barcodes: tuple[str, ...] = ()) -> frozenset[str]:
    keys: set[str] = set()
    for code in barcodes:
        keys.add("bc:" + re.sub(r"\s+", "", code.upper()))
    for match in IMB_HUMAN.finditer(text.upper()):
        keys.add("imb:" + re.sub(r"[\s\-]+", "", match.group(0)))
    for match in ACCOUNT.finditer(text):
        keys.add("acct:" + match.group(1))
    for match in INVOICE.finditer(text):
        keys.add("inv:" + match.group(1).upper())
    return frozenset(keys)


def identity_conflict(prev: frozenset[str], curr: frozenset[str]) -> bool:
    """True when both pages have the same kind of id and they disagree."""
    for kind in ("acct:", "inv:", "imb:", "bc:"):
        left = {key for key in prev if key.startswith(kind)}
        right = {key for key in curr if key.startswith(kind)}
        if left and right and left.isdisjoint(right):
            return True
    return False


def page_of(text: str) -> tuple[int, int] | None:
    match = PAGE_OF.search(text[:1200] if text else "")
    if match is None:
        return None
    current, total = int(match.group(1)), int(match.group(2))
    if current <= 0 or total <= 0 or current > total + 3:
        return None
    return current, total


def _year(value: int) -> int:
    if value < 100:
        return value + 2000 if value < 70 else value + 1900
    return value


def make_iso_date(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def plausible_iso(iso: str, *, allow_future_days: int = 14) -> bool:
    if not ISO_DATE.match(iso):
        return False
    parsed = date.fromisoformat(iso)
    today = date.today()
    return date(1990, 1, 1) <= parsed <= today + timedelta(days=allow_future_days)


def extract_date_spans(text: str) -> list[tuple[str, int, int]]:
    found: list[tuple[str, int, int]] = []
    for match in DATE_LONG.finditer(text):
        month = MONTH_NUM.get(match.group(1).lower().rstrip("."))
        if month is None:
            continue
        iso = make_iso_date(_year(int(match.group(3))), month, int(match.group(2)))
        if iso and plausible_iso(iso, allow_future_days=400):
            found.append((iso, match.start(), match.end()))
    for match in DATE_US.finditer(text):
        iso = make_iso_date(
            _year(int(match.group(3))), int(match.group(1)), int(match.group(2))
        )
        if iso and plausible_iso(iso, allow_future_days=400):
            found.append((iso, match.start(), match.end()))
    for match in DATE_ISO_FIND.finditer(text):
        iso = match.group(1)
        if plausible_iso(iso, allow_future_days=400):
            found.append((iso, match.start(), match.end()))
    return found


def extract_due_date(text: str) -> str | None:
    for match in DUE_CUE.finditer(text):
        window = text[match.end() : match.end() + 80]
        for iso, _, _ in extract_date_spans(window):
            if plausible_iso(iso, allow_future_days=400):
                return iso
    return None


def extract_doc_date(text: str, due: str | None) -> str | None:
    for match in STATEMENT_CUE.finditer(text):
        window = text[match.end() : match.end() + 80]
        for iso, _, _ in extract_date_spans(window):
            if iso != due and plausible_iso(iso, allow_future_days=14):
                return iso
    today = date.today().isoformat()
    past = [
        iso
        for iso, _, _ in extract_date_spans(text)
        if iso != due and iso <= today and plausible_iso(iso, allow_future_days=14)
    ]
    return max(past) if past else None


def extract_amount(text: str) -> str | None:
    match = AMOUNT_CUE.search(text)
    return match.group(1).replace(",", "") if match else None


def guess_doc_type(text: str) -> str:
    hay = text.lower()
    best = "other"
    best_n = 0
    for dtype, hints in DOC_TYPE_HINTS:
        hits = sum(1 for hint in hints if hint in hay)
        if hits > best_n:
            best, best_n = dtype, hits
    return best


def letterhead_issuer(text: str) -> str | None:
    skip = ("identity keys", "page ", "http", "www.")
    for raw in text.splitlines()[:20]:
        line = raw.strip()
        if len(line) < 5 or len(line) > 80:
            continue
        low = line.lower()
        if low.startswith(skip):
            continue
        if LETTERHEAD.search(line):
            cleaned = sanitize_filename_part(line, fallback="")
            return cleaned or None
        letters = re.sub(r"[^A-Za-z]", "", line)
        if (
            len(letters) >= 8
            and line == line.upper()
            and any(ch.isalpha() for ch in line)
        ):
            cleaned = sanitize_filename_part(line.title(), fallback="")
            return cleaned or None
    return None


def hay_has_phrase(hay: str, needle: str) -> bool:
    needle = needle.strip()
    if not needle:
        return False
    return (
        re.search(r"\b" + re.escape(needle) + r"\b", hay, flags=re.IGNORECASE)
        is not None
    )


def issuer_map_hit(
    text: str, taxonomy: dict[str, Any]
) -> tuple[str | None, str | None]:
    hay = text.lower()
    best: tuple[int, str, str] | None = None
    for issuer in taxonomy.get("issuers") or []:
        folder = str(issuer.get("folder") or "").strip() or None
        for match in issuer.get("match") or []:
            needle = str(match).strip()
            if not needle or not hay_has_phrase(hay, needle):
                continue
            cand = (len(needle), folder or "", needle)
            if best is None or cand[0] > best[0]:
                best = cand
    if best is None:
        return None, None
    folder, label = best[1] or None, best[2]
    if label.islower():
        label = label.title()
    return folder, label


def identity_index_keys(
    identity: list[str] | frozenset[str], doc_date: str | None
) -> list[str]:
    out: list[str] = []
    for key in identity:
        if key.startswith(("imb:", "bc:")):
            out.append(key)
        elif key.startswith(("acct:", "inv:")):
            out.append(f"{key}|{doc_date or ''}")
        else:
            out.append(key)
    return out


def prior_identity_hit(
    keys: list[str] | frozenset[str],
    doc_date: str | None,
    index: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    for lookup in identity_index_keys(keys, doc_date):
        rec = index.get(lookup)
        if rec:
            return rec
    return None


def make_signals(
    path: Path,
    *,
    text: str | None = None,
    text_of: Callable[[Path], str] | None = None,
) -> PageSignals:
    raw = (
        text
        if text is not None
        else (text_of(path) if text_of else tesseract_text(path))
    )
    codes = zbar_barcodes(path)
    return PageSignals(
        path=path,
        text=raw,
        dhash=dhash_int(path),
        barcodes=codes,
        identity=identity_keys(raw, codes),
        tokens=distinctive_tokens(raw),
    )


def token_jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def token_coverage(source: frozenset[str], dest: frozenset[str]) -> float:
    if not source:
        return 0.0
    return len(source & dest) / len(source)


def relate_pages(
    prev: PageSignals, curr: PageSignals, taxonomy: dict[str, Any]
) -> tuple[str, str]:
    """Classify curr vs prev: drop, quarantine, split, or keep."""
    extra = curr.tokens - prev.tokens
    coverage = token_coverage(prev.tokens, curr.tokens)
    jac = token_jaccard(prev.tokens, curr.tokens)
    dist = hamming64(prev.dhash, curr.dhash) if prev.dhash and curr.dhash else 64
    same_id = bool(prev.identity and curr.identity and (prev.identity & curr.identity))
    extra_needed = max(8, int(0.15 * max(len(prev.tokens), 1)))
    if coverage >= 0.5 and len(extra) >= extra_needed:
        return "quarantine", f"double-feed overlay of {prev.path.name}"
    po_prev = page_of(prev.text)
    po_curr = page_of(curr.text)
    if (
        po_prev
        and po_curr
        and po_prev[1] == po_curr[1]
        and po_curr[0] == po_prev[0] + 1
    ):
        return "keep", "page sequence"
    if identity_conflict(prev.identity, curr.identity):
        return "split", "different identity (barcode/account)"
    if (
        dist <= 6
        or (jac >= 0.88 and len(extra) < 8)
        or (same_id and jac >= 0.75 and len(extra) < 8)
    ):
        return "drop", f"duplicate of {prev.path.name}"
    curr_head = curr.text[:800]
    if CONTINUATION.search(curr_head) and (same_id or jac >= 0.3):
        return "keep", "continuation"
    prev_iss = issuer_folder(prev.text, taxonomy)
    curr_iss = issuer_folder(curr.text, taxonomy)
    if prev_iss and curr_iss and prev_iss != curr_iss:
        return "split", "issuer map"
    if (
        NEW_DOC_START.search(curr_head)
        and not NEW_DOC_START.search(prev.text[:800])
        and not CONTINUATION.search(curr_head)
    ):
        return "split", "page-1 start"
    if (
        jac < 0.18
        and not CONTINUATION.search(curr_head)
        and prev.tokens
        and curr.tokens
    ):
        return "split", f"text jaccard {jac:.2f}"
    return "keep", f"jaccard {jac:.2f}"


def should_split_on_text(prev: str, curr: str, taxonomy: dict[str, Any]) -> bool:
    dummy = Path("page_0000.png")
    action, _reason = relate_pages(
        make_signals(dummy, text=prev),
        make_signals(Path("page_0001.png"), text=curr),
        taxonomy,
    )
    return action == "split"


def llm_is_new_document(
    prev: str,
    curr: str,
    *,
    llm_url: str,
    model: str,
    temperature: float,
    max_tokens: int,
) -> bool:
    if len(prev.strip()) < 20 or len(curr.strip()) < 20:
        return False
    prompt = f"""Two consecutive scanned pages. Return only JSON.
Page A:
{prev[:1500]}

Page B:
{curr[:1500]}

Is page B a NEW document (different letter, form, or issuer) rather than the next page of page A?
{{"new_document": false, "confidence": 0.0}}
new_document true only when B is clearly a different document. Continuation, page 2, or the reverse of A is false.
"""
    content = llm_complete(
        llm_url, model, prompt, temperature=temperature, max_tokens=max_tokens
    )
    parsed = extract_json_object(content)
    try:
        confidence = float(parsed.get("confidence") or 0)
    except (TypeError, ValueError):
        confidence = 0.0
    return bool(parsed.get("new_document")) and confidence >= 0.8


def split_groups_by_content(
    groups: list[list[Path]],
    *,
    taxonomy: dict[str, Any],
    text_of: Callable[[Path], str],
    fronts: set[Path],
    llm_new_doc: Callable[[str, str], bool] | None = None,
) -> list[list[Path]]:
    docs, _review = segment_stack(
        groups,
        taxonomy=taxonomy,
        text_of=text_of,
        fronts=fronts,
        llm_new_doc=llm_new_doc,
    )
    return docs


def sheets_in_group(group: list[Path], fronts: set[Path]) -> list[list[Path]]:
    sheets: list[list[Path]] = []
    current: list[Path] = []
    for page in group:
        if page in fronts and current:
            sheets.append(current)
            current = [page]
        else:
            current.append(page)
    if current:
        sheets.append(current)
    return sheets


def segment_stack(
    groups: list[list[Path]],
    *,
    taxonomy: dict[str, Any],
    text_of: Callable[[Path], str],
    fronts: set[Path],
    llm_new_doc: Callable[[str, str], bool] | None = None,
) -> tuple[list[list[Path]], list[list[Path]]]:
    """Split a mixed mail stack: drop rescans, quarantine overlays, split docs."""
    docs: list[list[Path]] = []
    review: list[list[Path]] = []
    history: list[PageSignals] = []
    cache: dict[Path, PageSignals] = {}

    def signals_for(path: Path) -> PageSignals:
        if path not in cache:
            cache[path] = make_signals(path, text_of=text_of)
        return cache[path]

    for group in groups:
        current: list[Path] = []
        last: PageSignals | None = None
        for sheet in sheets_in_group(group, fronts):
            front = sheet[0]
            info = signals_for(front)
            action, reason = "keep", "first sheet"
            for prior in history:
                act, why = relate_pages(prior, info, taxonomy)
                if act in {"drop", "quarantine"}:
                    action, reason = act, why
                    break
            if action not in {"drop", "quarantine"} and last is not None:
                action, reason = relate_pages(last, info, taxonomy)
                if (
                    action == "keep"
                    and llm_new_doc is not None
                    and token_jaccard(last.tokens, info.tokens) < 0.35
                    and llm_new_doc(last.text, info.text)
                ):
                    action, reason = "split", "llm new document"
            if action == "drop":
                eprint(f"   drop duplicate sheet {front.name} ({reason})")
                continue
            if action == "quarantine":
                eprint(f"   quarantine {front.name} ({reason})")
                if current:
                    docs.append(current)
                    current = []
                    last = None
                review.append(sheet)
                history.append(info)
                continue
            if action == "split" and current:
                eprint(f"   content-split before {front.name} ({reason})")
                docs.append(current)
                current = []
            current.extend(sheet)
            last = info
            history.append(info)
        if current:
            docs.append(current)
    return docs, review


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """Minimal YAML for taxonomy files (scalars, string lists, issuer maps)."""
    data: dict[str, Any] = {}
    key: str | None = None
    issuer: dict[str, Any] | None = None
    for raw in text.splitlines():
        if "#" in raw:
            raw = raw[: raw.index("#")]
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if indent == 0 and ":" in line:
            issuer = None
            key, _, rest = line.partition(":")
            key = key.strip()
            rest = rest.strip()
            if rest:
                data[key] = _yaml_scalar(rest)
            elif key in {"issuers", "folders", "doc_types"}:
                data[key] = []
            else:
                data[key] = None
            continue
        if key is None:
            continue
        if line.startswith("- "):
            item = line[2:].strip()
            if key == "issuers":
                issuer = {}
                data.setdefault("issuers", []).append(issuer)
                if item and item != "{}" and ":" in item:
                    ik, _, iv = item.partition(":")
                    issuer[ik.strip()] = _yaml_scalar(iv.strip())
            else:
                data.setdefault(key, []).append(_yaml_scalar(item))
            continue
        if issuer is not None and ":" in line:
            ik, _, iv = line.partition(":")
            issuer[ik.strip()] = _yaml_scalar(iv.strip())
    return data


def _yaml_scalar(value: str) -> Any:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_yaml_scalar(part) for part in inner.split(",")]
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.lower() in {"null", "~", ""}:
        return None
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def load_taxonomy(path: Path | None) -> dict[str, Any]:
    default: dict[str, Any] = {
        "root": str(Path.home() / "Documents"),
        "inbox": "Inbox/scans",
        "due_dir": "Inbox/due",
        "review": "Inbox/needs-review",
        "min_confidence": 0.75,
        "doc_types": list(DOC_TYPES),
        "folders": [],
        "issuers": [],
    }
    if path is None or not path.is_file():
        return default
    text = path.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if stripped.startswith("{"):
        loaded = json.loads(text)
    else:
        loaded = parse_simple_yaml(text)
    if isinstance(loaded, dict):
        default.update(loaded)
    return default


def resolve_taxonomy_path(explicit: str | None) -> Path | None:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    env = os.environ.get("ADF_OCR_TAXONOMY")
    if env:
        candidates.append(Path(env).expanduser())
    xdg = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    candidates.append(Path(xdg) / "adf-ocr" / "taxonomy.yaml")
    here = Path(__file__).resolve().parent
    candidates.append(here.parent / "share" / "adf-ocr" / "taxonomy.example.yaml")
    for cand in candidates:
        if cand.is_file():
            return cand
    return None


def expand_root(raw: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(raw))).resolve()


def allowed_folders(taxonomy: dict[str, Any], root: Path) -> list[str]:
    named = [str(x) for x in taxonomy.get("folders") or [] if str(x).strip()]
    for issuer in taxonomy.get("issuers") or []:
        folder = str(issuer.get("folder") or "").strip()
        if folder and folder not in named:
            named.append(folder)
    if not named:
        named = (
            [p.name for p in sorted(root.iterdir()) if p.is_dir()]
            if root.is_dir()
            else []
        )
    if "." not in named:
        named.append(".")
    return named


def issuer_folder(text: str, taxonomy: dict[str, Any]) -> str | None:
    folder, _label = issuer_map_hit(text, taxonomy)
    return folder


def heuristic_classify(
    text: str, taxonomy: dict[str, Any], folders: list[str]
) -> dict[str, Any]:
    folder, label = issuer_map_hit(text, taxonomy)
    mapped = bool(folder)
    dtype = guess_doc_type(text)
    due = extract_due_date(text)
    doc_date = extract_doc_date(text, due)
    amount = extract_amount(text)
    issuer = label or letterhead_issuer(text) or "Unknown"
    if mapped:
        confidence = 0.9 if dtype != "other" or doc_date else 0.85
    elif issuer != "Unknown" and dtype != "other":
        confidence = 0.8 if doc_date else 0.72
    elif dtype != "other":
        confidence = 0.55
    else:
        confidence = 0.35
    if folder and folder not in folders:
        folder = ""
        confidence = min(confidence, 0.5)
    if issuer != "Unknown" and dtype != "other":
        title = f"{issuer} {dtype.title()}"
    elif issuer != "Unknown":
        title = f"{issuer} Document"
    else:
        title = "Scanned Document"
    slug = sanitize_filename_part(title.lower().replace(" ", "-"), fallback="document")
    return {
        "doc_type": dtype,
        "issuer": issuer,
        "folder": folder or "",
        "doc_date": doc_date,
        "due_date": due,
        "amount": amount,
        "title": title,
        "author": issuer,
        "subject": dtype.title() if dtype != "other" else "Scanned Document",
        "keywords": ",".join(
            part for part in (dtype, issuer.lower().replace(" ", "-")) if part
        ),
        "base_name": slug[:80],
        "confidence": confidence,
        "issuer_map": mapped,
        "classify_source": "heuristic",
    }


def merge_llm_over_heuristic(
    heur: dict[str, Any], parsed: dict[str, Any]
) -> dict[str, Any]:
    out = dict(heur)
    for key in (
        "doc_type",
        "issuer",
        "folder",
        "doc_date",
        "due_date",
        "amount",
        "title",
        "author",
        "subject",
        "keywords",
        "base_name",
    ):
        val = parsed.get(key)
        if val in (None, "", "null"):
            continue
        if key == "issuer" and str(val).strip().lower() in {"unknown"}:
            continue
        if key == "folder" and heur.get("issuer_map"):
            continue
        out[key] = val
    try:
        conf = float(parsed.get("confidence"))
        out["confidence"] = max(float(heur.get("confidence") or 0), min(1.0, conf))
    except (TypeError, ValueError):
        pass
    out["classify_source"] = "llm"
    return out


def extract_json_object(text: str) -> dict[str, Any]:
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def llm_complete(
    url: str, model: str, prompt: str, *, temperature: float, max_tokens: int
) -> str:
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    ).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        eprint(f"adf-ocr-file: LLM request failed ({exc})")
        return ""
    try:
        return str(body["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError):
        return ""


def classify_text(
    text: str,
    taxonomy: dict[str, Any],
    folders: list[str],
    *,
    llm_url: str,
    models: list[str],
    temperature: float,
    max_tokens: int,
    use_llm: bool = True,
) -> dict[str, Any]:
    result = heuristic_classify(text, taxonomy, folders)
    parsed: dict[str, Any] = {}
    if use_llm and float(result["confidence"]) < 0.85:
        snippet = text[:15000]
        folder_list = ", ".join(folders)
        types = ", ".join(taxonomy.get("doc_types") or DOC_TYPES)
        hint = json.dumps(
            {
                key: result.get(key)
                for key in (
                    "doc_type",
                    "issuer",
                    "folder",
                    "doc_date",
                    "due_date",
                    "amount",
                    "title",
                )
            }
        )
        prompt = f"""You are a document archivist. Analyze the text and return only valid JSON.
Prefer the CLI heuristic when it looks correct. Do not add glosses like "(implied ...)".

Heuristic:
{hint}

Text:
{snippet}

Return this exact JSON:
{{
  "doc_type": "one of: {types}",
  "issuer": "company or agency or Unknown",
  "folder": "one of: {folder_list}",
  "doc_date": "YYYY-MM-DD or null",
  "due_date": "YYYY-MM-DD or null if no payment due",
  "amount": "number string or null",
  "title": "Full clear title",
  "author": "Company or person or Unknown",
  "subject": "Document type or short description",
  "keywords": "comma,separated,keywords",
  "base_name": "short-filename-slug",
  "confidence": 0.0
}}
folder must be exactly one allowlisted folder or "." for the documents root.
due_date only when the page states a bill or payment due date.
confidence is 0 to 1.
"""
        for model in models:
            if not model:
                continue
            content = llm_complete(
                llm_url, model, prompt, temperature=temperature, max_tokens=max_tokens
            )
            parsed = extract_json_object(content)
            if parsed:
                result = merge_llm_over_heuristic(result, parsed)
                break
    if result["doc_type"] not in (taxonomy.get("doc_types") or DOC_TYPES):
        result["doc_type"] = "other"
    try:
        conf = float(result["confidence"])
    except (TypeError, ValueError):
        conf = 0.4 if parsed else float(result.get("confidence") or 0.35)
    result["confidence"] = max(0.0, min(1.0, conf))
    result["issuer"] = clean_issuer_name(str(result.get("issuer") or "Unknown"))
    if not result.get("issuer_map") and result.get("folder") == ".":
        result["confidence"] = min(result["confidence"], 0.7)
    if result.get("folder") not in folders:
        result["folder"] = ""
        result["confidence"] = min(result["confidence"], 0.5)
    for key in ("doc_date", "due_date"):
        val = result.get(key)
        if val is None or val == "null":
            result[key] = None
        else:
            val_s = str(val)[:10]
            result[key] = val_s if ISO_DATE.match(val_s) else None
    return result


def clean_issuer_name(value: str) -> str:
    cleaned = re.sub(r"\s*\(implied[^)]*\)", "", value, flags=re.IGNORECASE).strip()
    return cleaned or "Unknown"


def sanitize_filename_part(value: str, *, fallback: str) -> str:
    cleaned = SAFE_NAME.sub(" ", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ._")
    return cleaned[:120] or fallback


def build_filename(meta: dict[str, Any], scan_day: str) -> str:
    day = meta.get("doc_date") or scan_day
    issuer = sanitize_filename_part(
        str(meta.get("issuer") or "Unknown"), fallback="Unknown"
    )
    title = sanitize_filename_part(
        str(meta.get("title") or meta.get("base_name") or "Document"),
        fallback="Document",
    )
    return f"{day} - {issuer} - {title}.pdf"


def unique_dest(directory: Path, name: str) -> Path:
    dest = directory / name
    if not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    for i in range(2, 100):
        candidate = directory / f"{stem} - {i}{suffix}"
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"too many collisions in {directory}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ics_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def write_ics(
    path: Path,
    *,
    due: str,
    summary: str,
    description: str,
    uid: str,
) -> None:
    due_d = date.fromisoformat(due)
    end = due_d + timedelta(days=1)
    now = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//adf-ocr//EN",
        "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now}",
        f"DTSTART;VALUE=DATE:{due_d.strftime('%Y%m%d')}",
        f"DTEND;VALUE=DATE:{end.strftime('%Y%m%d')}",
        f"SUMMARY:{ics_escape(summary)}",
        f"DESCRIPTION:{ics_escape(description)}",
        "TRANSP:TRANSPARENT",
        "END:VEVENT",
        "END:VCALENDAR",
        "",
    ]
    path.write_text("\r\n".join(lines), encoding="utf-8")


def ocr_group(pages: list[Path], work: Path, *, rotate_threshold: str) -> Path:
    intermediate = work / "intermediate.pdf"
    out_pdf = work / "ocr.pdf"
    img2pdf = shutil.which("img2pdf")
    ocrmypdf = shutil.which("ocrmypdf")
    if img2pdf is None or ocrmypdf is None:
        raise RuntimeError("img2pdf and ocrmypdf are required")
    run(
        [img2pdf, *[str(p) for p in pages], "-o", str(intermediate)],
        timeout=120,
        check=True,
    )
    run(
        [
            ocrmypdf,
            "--language",
            "eng",
            "--rotate-pages",
            "--rotate-pages-threshold",
            rotate_threshold,
            "--deskew",
            "--clean",
            "--optimize",
            "1",
            "--force-ocr",
            str(intermediate),
            str(out_pdf),
        ],
        timeout=900,
        check=True,
    )
    return out_pdf


def pdftotext(pdf: Path) -> str:
    binary = shutil.which("pdftotext")
    if binary is None:
        return ""
    proc = run([binary, str(pdf), "-"], timeout=60)
    return proc.stdout if proc.returncode == 0 else ""


ADF_PDF_NAME = re.compile(r"^\d{4}-\d{2}-\d{2} - .+\.pdf$")


def _info_str(info: object, name: str) -> str:
    getter = getattr(info, "get", None)
    if getter is None:
        return ""
    try:
        val = getter(name)
    except (KeyError, TypeError, ValueError, AttributeError):
        return ""
    return str(val) if val is not None else ""


def embed_pdf_metadata(
    pdf: Path,
    meta: dict[str, Any],
    *,
    identity: list[str] | None = None,
    digest: str = "",
    pages: int = 0,
    flags: list[str] | None = None,
    review: bool = False,
) -> None:
    title = str(meta.get("title") or "Scanned Document")
    author = str(meta.get("issuer") or meta.get("author") or "Unknown")
    subject = str(meta.get("subject") or meta.get("doc_type") or "Scanned Document")
    keywords = str(meta.get("keywords") or "scanned")
    try:
        import pikepdf
    except ImportError:
        binary = shutil.which("exiftool")
        if binary is None:
            return
        run(
            [
                binary,
                "-overwrite_original",
                f"-Title={title}",
                f"-Author={author}",
                f"-Subject={subject}",
                f"-Keywords={keywords}",
                "-Creator=adf-ocr",
                str(pdf),
            ],
            timeout=30,
        )
        return
    tmp = pdf.with_suffix(".pdf.meta")
    with pikepdf.open(pdf) as doc:
        info = doc.docinfo
        info["/Title"] = title
        info["/Author"] = author
        info["/Subject"] = subject
        info["/Keywords"] = keywords
        info["/Creator"] = "adf-ocr"
        info["/ADFDocType"] = str(meta.get("doc_type") or "")
        info["/ADFDocDate"] = str(meta.get("doc_date") or "")
        info["/ADFDueDate"] = str(meta.get("due_date") or "")
        info["/ADFAmount"] = str(meta.get("amount") or "")
        info["/ADFSha256"] = digest
        info["/ADFIdentity"] = "|".join(identity or [])
        info["/ADFPages"] = str(pages)
        info["/ADFConfidence"] = str(meta.get("confidence") or "")
        info["/ADFSource"] = str(meta.get("classify_source") or "")
        info["/ADFFlags"] = ",".join(flags or [])
        info["/ADFReview"] = "1" if review else "0"
        if meta.get("split_reason"):
            info["/ADFSplitReason"] = str(meta.get("split_reason"))
        with doc.open_metadata() as xmp:
            xmp["dc:title"] = title
            xmp["dc:creator"] = [author]
            xmp["dc:description"] = subject
            xmp["pdf:Keywords"] = keywords
        doc.save(tmp)
    tmp.replace(pdf)


def read_pdf_filing_meta(path: Path) -> dict[str, Any] | None:
    try:
        import pikepdf
    except ImportError:
        return None
    try:
        with pikepdf.open(path) as doc:
            info = doc.docinfo
            creator = _info_str(info, "/Creator")
            digest = _info_str(info, "/ADFSha256")
            if creator != "adf-ocr" and not digest:
                return None
            ident = [
                part for part in _info_str(info, "/ADFIdentity").split("|") if part
            ]
            doc_date = _info_str(info, "/ADFDocDate") or None
            return {
                "dest": str(path),
                "sha256": digest,
                "doc_date": doc_date,
                "identity": ident,
            }
    except (OSError, ValueError, TypeError):
        return None


def folder_dir(root: Path, folder: str, inbox: str, *, high_confidence: bool) -> Path:
    if high_confidence and folder == ".":
        return root
    if high_confidence and folder:
        dest = root / folder
        if dest.is_dir():
            return dest
    return root / inbox


def filing_search_dirs(
    root: Path, taxonomy: dict[str, Any], folders: list[str]
) -> list[Path]:
    rels: list[str] = []
    for key in ("inbox", "review", "due_dir"):
        rel = str(taxonomy.get(key) or "").strip()
        if rel:
            rels.append(rel)
    rels.extend(folder for folder in folders if folder and folder != ".")
    dirs: list[Path] = [root]
    seen = {root.resolve()}
    for rel in rels:
        path = (root / rel).resolve()
        if path in seen or not path.is_dir():
            continue
        seen.add(path)
        dirs.append(path)
    return dirs


def load_filing_index(
    root: Path, taxonomy: dict[str, Any], folders: list[str]
) -> dict[str, Any]:
    by_key: dict[str, dict[str, Any]] = {}
    digests: set[str] = set()
    index = {"by_key": by_key, "sha256": digests}
    for base in filing_search_dirs(root, taxonomy, folders):
        for pdf in base.rglob("*.pdf"):
            if not ADF_PDF_NAME.match(pdf.name):
                continue
            rec = read_pdf_filing_meta(pdf)
            if rec is None:
                continue
            remember_filing(
                index,
                dest=Path(rec["dest"]),
                digest=str(rec.get("sha256") or ""),
                doc_date=rec.get("doc_date"),
                identity=rec.get("identity") or [],
            )
    return index


def remember_filing(
    index: dict[str, Any] | None,
    *,
    dest: Path,
    digest: str,
    doc_date: str | None,
    identity: list[str] | None,
) -> None:
    if index is None:
        return
    rec = {"dest": str(dest), "doc_date": doc_date, "sha256": digest}
    if digest:
        index["sha256"].add(digest)
    for lookup in identity_index_keys(identity or [], doc_date):
        index["by_key"][lookup] = rec


def write_batch_manifest(
    pages_dir: Path,
    root: Path,
    taxonomy: dict[str, Any],
    results: list[dict[str, Any]],
) -> Path:
    counts: dict[str, int] = {}
    for row in results:
        status = str(row.get("status") or "unknown")
        if row.get("review"):
            status = "review"
        counts[status] = counts.get(status, 0) + 1
    payload = {
        "scanned_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "pages_dir": str(pages_dir),
        "counts": counts,
        "results": results,
    }
    path = pages_dir / "manifest.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    eprint(f"Batch manifest {path}")
    return path


def file_pdf(
    pdf: Path,
    meta: dict[str, Any],
    *,
    taxonomy: dict[str, Any],
    root: Path,
    folders: list[str],
    min_confidence: float,
    pages: int,
    review: bool = False,
    flags: list[str] | None = None,
    split_reason: str | None = None,
    identity: list[str] | None = None,
    filing_index: dict[str, Any] | None = None,
) -> dict[str, Any]:
    inbox = str(taxonomy.get("inbox") or "Inbox/scans")
    due_rel = str(taxonomy.get("due_dir") or "Inbox/due")
    review_rel = str(taxonomy.get("review") or "Inbox/needs-review")
    high = float(meta["confidence"]) >= min_confidence and bool(meta.get("folder"))
    if high and meta["folder"] not in folders:
        high = False
    if review:
        high = False
        dest_dir = root / review_rel
    else:
        dest_dir = folder_dir(
            root, str(meta.get("folder") or ""), inbox, high_confidence=high
        )
    dest_dir.mkdir(parents=True, exist_ok=True)
    scan_day = date.today().isoformat()
    name = build_filename(meta, scan_day)
    dest = unique_dest(dest_dir, name)
    digest = sha256_file(pdf)
    if filing_index:
        ident_hit = prior_identity_hit(
            identity or [], meta.get("doc_date"), filing_index["by_key"]
        )
        if ident_hit:
            return {
                "status": "duplicate",
                "dest": ident_hit.get("dest"),
                "sha256": digest,
                "confidence": meta["confidence"],
                "folder": meta.get("folder") or inbox,
                "reason": "identity",
            }
        if digest in filing_index["sha256"]:
            return {
                "status": "duplicate",
                "dest": str(dest_dir),
                "sha256": digest,
                "confidence": meta["confidence"],
                "folder": meta.get("folder") or inbox,
                "reason": "sha256",
            }
    for existing in dest_dir.glob("*.pdf"):
        try:
            if sha256_file(existing) == digest:
                return {
                    "status": "duplicate",
                    "dest": str(existing),
                    "sha256": digest,
                    "confidence": meta["confidence"],
                    "folder": meta.get("folder") or inbox,
                    "reason": "sha256",
                }
        except OSError:
            continue
    shutil.copy2(pdf, dest)
    meta_stamp = dict(meta)
    if split_reason:
        meta_stamp["split_reason"] = split_reason
    embed_pdf_metadata(
        dest,
        meta_stamp,
        identity=identity or [],
        digest=digest,
        pages=pages,
        flags=flags or [],
        review=review,
    )
    remember_filing(
        filing_index,
        dest=dest,
        digest=digest,
        doc_date=meta.get("doc_date"),
        identity=identity,
    )
    ics_path = None
    due = meta.get("due_date")
    if due:
        uid = f"adf-ocr-{digest[:16]}@localhost"
        summary = (
            f"{meta.get('issuer') or 'Bill'} due: {meta.get('title') or dest.stem}"
        )
        description = f"amount={meta.get('amount')}\nfile={dest}"
        ics_file = dest.with_suffix(".ics")
        write_ics(ics_file, due=due, summary=summary, description=description, uid=uid)
        due_dir = root / due_rel
        due_dir.mkdir(parents=True, exist_ok=True)
        due_copy = unique_dest(due_dir, ics_file.name)
        shutil.copy2(ics_file, due_copy)
        ics_path = str(ics_file)
    return {
        "status": "filed",
        "dest": str(dest),
        "ics": ics_path,
        "sha256": digest,
        "confidence": meta["confidence"],
        "folder": meta.get("folder") or inbox,
        "inbox": not high,
        "review": review,
        "due_date": due,
        "flags": flags or [],
    }


def process_pages_dir(
    pages_dir: Path, args: argparse.Namespace
) -> list[dict[str, Any]]:
    tax_path = resolve_taxonomy_path(args.taxonomy)
    taxonomy = load_taxonomy(tax_path)
    if args.out_root:
        taxonomy["root"] = args.out_root
    root = expand_root(str(taxonomy["root"]))
    root.mkdir(parents=True, exist_ok=True)
    folders = allowed_folders(taxonomy, root)
    filing_index = load_filing_index(root, taxonomy, folders)
    use_llm = not (getattr(args, "no_llm", False) or env_flag("ADF_OCR_NO_LLM", False))
    min_conf = float(
        args.min_confidence
        if args.min_confidence is not None
        else taxonomy.get("min_confidence") or 0.75
    )
    fmt = os.environ.get("SCAN_FORMAT", "png")
    pages = sorted(pages_dir.glob(f"page_*.{fmt}"))
    if not pages:
        pages = sorted(pages_dir.glob("page_*.png")) + sorted(
            pages_dir.glob("page_*.tiff")
        )
    if not pages:
        raise SystemExit(f"No page_*.{fmt} in {pages_dir}")

    def blank(path: Path) -> bool:
        return is_blank_page(
            path,
            margin=int(os.environ.get("MARGIN_TO_SHAVE", "80")),
            blur=int(os.environ.get("BLUR_RADIUS", "12")),
            fuzz=os.environ.get("FUZZ_PERCENT", "20%"),
            min_width=int(os.environ.get("MIN_CONTENT_WIDTH", "120")),
            min_height=int(os.environ.get("MIN_CONTENT_HEIGHT", "80")),
        )

    duplex = args.duplex if args.duplex is not None else env_flag("SCAN_DUPLEX", True)
    content_split = (
        args.content_split
        if args.content_split is not None
        else env_flag("ADF_OCR_CONTENT_SPLIT", True)
    )
    groups = group_pages(pages, blank, duplex=duplex)
    eprint(
        f"=== Grouped {len(pages)} page(s) → {len(groups)} blank-split stack(s) "
        f"(duplex={duplex}) ==="
    )
    models: list[str] = []
    for model in (
        args.classify_model
        or os.environ.get("ADF_OCR_CLASSIFY_MODEL")
        or os.environ.get("LLM_MODEL")
        or "gemma4:e2b",
        os.environ.get("LLM_MODEL") or "gemma4:e2b",
    ):
        if model and model not in models:
            models.append(model)
    llm_url = (
        args.llm_url
        or os.environ.get("LLM_SERVER_URL")
        or "http://127.0.0.1:11434/v1/chat/completions"
    )
    review_groups: list[list[Path]] = []
    if content_split and groups:
        fronts = sheet_fronts(pages, duplex=duplex)
        text_of = memo_tesseract()
        split_model = os.environ.get("LLM_MODEL") or "gemma4:e2b"

        def llm_new(prev: str, curr: str) -> bool:
            return llm_is_new_document(
                prev,
                curr,
                llm_url=llm_url,
                model=split_model,
                temperature=float(os.environ.get("LLM_TEMPERATURE") or 0.3),
                max_tokens=min(int(os.environ.get("LLM_MAX_TOKENS") or 2000), 200),
            )

        groups, review_groups = segment_stack(
            groups,
            taxonomy=taxonomy,
            text_of=text_of,
            fronts=fronts,
            llm_new_doc=llm_new if use_llm else None,
        )
        eprint(
            f"=== After mail split: {len(groups)} document(s), "
            f"{len(review_groups)} review sheet(s) ==="
        )
    if not groups and not review_groups:
        raise SystemExit("All pages looked blank")
    rotate = os.environ.get("OCR_ROTATE_THRESHOLD") or "12"
    results: list[dict[str, Any]] = []
    jobs: list[tuple[list[Path], bool, list[str]]] = [
        (group, False, []) for group in groups
    ]
    jobs.extend((group, True, ["double_feed"]) for group in review_groups)
    keep = False
    for index, (group, is_review, flags) in enumerate(jobs, start=1):
        kind = "review" if is_review else "document"
        eprint(f"=== {kind} {index}/{len(jobs)} ({len(group)} page(s)) ===")
        with tempfile.TemporaryDirectory(prefix=f"adf-ocr-doc{index}-") as tmp:
            work = Path(tmp)
            try:
                pdf = ocr_group(group, work, rotate_threshold=str(rotate))
            except (subprocess.CalledProcessError, RuntimeError) as exc:
                eprint(f"OCR failed for {kind} {index}: {exc}")
                results.append(
                    {"status": "ocr_failed", "pages": [str(p) for p in group]}
                )
                keep = True
                continue
            text = pdftotext(pdf)
            ident = sorted(identity_keys(text))
            if ident:
                text = "Identity keys: " + ", ".join(ident) + "\n\n" + text
            meta = classify_text(
                text,
                taxonomy,
                folders,
                llm_url=llm_url,
                models=models,
                temperature=float(os.environ.get("LLM_TEMPERATURE") or 0.3),
                max_tokens=int(os.environ.get("LLM_MAX_TOKENS") or 2000),
                use_llm=use_llm,
            )
            eprint(
                f"   classify {meta.get('classify_source')} "
                f"{meta.get('issuer')} {meta.get('doc_type')} "
                f"conf={meta.get('confidence')}"
            )
            filed = file_pdf(
                pdf,
                meta,
                taxonomy=taxonomy,
                root=root,
                folders=folders,
                min_confidence=min_conf,
                pages=len(group),
                review=is_review,
                flags=flags,
                identity=ident,
                filing_index=filing_index,
            )
            results.append(filed)
            if is_review:
                keep = True
            eprint(f"→ {filed.get('status')} {filed.get('dest')}")
    if (
        keep
        or env_flag("ADF_OCR_KEEP_CACHE", False)
        or getattr(args, "keep_cache", False)
    ):
        (pages_dir / ".keep").write_text("review or keep-cache\n", encoding="utf-8")
        eprint(f"Keeping page cache {pages_dir}")
    write_batch_manifest(pages_dir, root, taxonomy, results)
    return results


def self_test() -> int:
    failures = 0

    def check(cond: bool, label: str) -> None:
        nonlocal failures
        if not cond:
            eprint(f"FAIL {label}")
            failures += 1
        else:
            eprint(f"ok   {label}")

    pages = [Path(f"page_{i:04d}.png") for i in range(1, 7)]
    blanks = {pages[2], pages[4], pages[5]}
    groups = group_pages(pages, lambda p: p in blanks, duplex=False)
    check(groups == [pages[0:2], [pages[3]]], "simplex blank pages split documents")
    check(
        group_pages(pages[:2], lambda _p: False, duplex=False) == [pages[:2]],
        "no blanks stays one document",
    )
    duplex_blanks = {pages[1], pages[3], pages[5]}
    check(
        group_pages(pages, lambda p: p in duplex_blanks, duplex=True)
        == [[pages[0], pages[2], pages[4]]],
        "duplex blank backs stay one document",
    )
    sep_blanks = {pages[1], pages[2], pages[3], pages[5]}
    check(
        group_pages(pages, lambda p: p in sep_blanks, duplex=True)
        == [[pages[0]], [pages[4]]],
        "blank duplex sheet splits documents",
    )
    odd = pages[:3]
    check(
        group_pages(odd, lambda p: p is odd[1], duplex=True) == [[odd[0], odd[2]]],
        "duplex odd last front joins after dropped back",
    )
    split_tax = {
        "issuers": [
            {"match": ["nevada dmv"], "folder": "DMV"},
            {"match": ["ascent credit union"], "folder": "AscentCU"},
        ]
    }
    check(
        should_split_on_text(
            "STATE OF NEVADA DMV TITLE FEE RECEIPT",
            "ASCENT CREDIT UNION ACCOUNT STATEMENT",
            split_tax,
        ),
        "content split on issuer change",
    )
    check(
        not should_split_on_text(
            "NEVADA DMV PAGE 1 OF 2",
            "continued page 2 of 2 more dmv text",
            split_tax,
        ),
        "continuation page does not split",
    )
    check(
        not should_split_on_text("short", "also short", split_tax),
        "unknown issuers stay together",
    )
    a, b, c = pages[0], pages[1], pages[2]
    mixed = split_groups_by_content(
        [[a, b, c]],
        taxonomy=split_tax,
        text_of=lambda p: {
            a: "NEVADA DMV TITLE FEE",
            b: "see reverse more dmv",
            c: "ASCENT CREDIT UNION STATEMENT",
        }[p],
        fronts={a, c},
    )
    check(mixed == [[a, b], [c]], "content split at next sheet front")
    avidia = (
        "Avidia Bank Hudson Health Savings Account statement account number 3026712731 "
        "paper surcharge benefit admin interest payment"
    )
    overlay = (
        "escalated Japan violating directive harm prevention imperative ranked higher "
        "Asimov Zeroth inaction legal brief " + avidia
    )
    act, _why = relate_pages(
        make_signals(Path("page_0001.png"), text=avidia),
        make_signals(Path("page_0003.png"), text=overlay),
        split_tax,
    )
    check(act == "quarantine", "double-feed overlay quarantines")
    weber_a = (
        "Weber State Credit Union Goldenwest activate contactless Ogden Adams "
        "9JFJRZZ1 0004 002538"
    )
    weber_b = (
        "Weber State Credit Union Goldenwest activate contactless Ogden Adams "
        "9JFK0VZ1 0001 000059"
    )
    act, _why = relate_pages(
        make_signals(Path("page_0005.png"), text=weber_a),
        make_signals(Path("page_0007.png"), text=weber_b),
        split_tax,
    )
    check(act == "split", "same-form mailers with different IMB split")
    act, _why = relate_pages(
        make_signals(Path("page_0001.png"), text=avidia),
        make_signals(Path("page_0009.png"), text=avidia),
        split_tax,
    )
    check(act == "drop", "identical rescan drops")
    if Image is not None:
        with tempfile.TemporaryDirectory() as img_tmp:
            tdir = Path(img_tmp)
            one = tdir / "a.png"
            two = tdir / "b.png"
            Image.new("RGB", (64, 64), (240, 240, 240)).save(one)
            Image.new("RGB", (64, 64), (240, 240, 240)).save(two)
            check(dhash_int(one) == dhash_int(two), "identical images share dHash")
            check(hamming64(dhash_int(one), dhash_int(two)) == 0, "dHash hamming 0")
    check(
        clean_issuer_name("WSCU (implied bank financial institution)") == "WSCU",
        "strip implied issuer gloss",
    )
    stmt = (
        "Avidia Bank account statement statement period ending September 30, 2026 "
        "account number 1111111111 amount due $42.00 pay by October 15, 2026 "
        "ending balance previous balance"
    )
    check(
        extract_doc_date(stmt, extract_due_date(stmt)) == "2026-09-30",
        "CLI statement date",
    )
    check(extract_due_date(stmt) == "2026-10-15", "CLI due date")
    check(extract_amount(stmt) == "42.00", "CLI amount due")
    check(guess_doc_type(stmt) == "statement", "CLI doc type statement")
    check(
        identity_conflict(
            frozenset({"imb:9JFJRZZ10004002538"}),
            frozenset({"imb:9JFK0VZ10001000059"}),
        ),
        "same-kind IMB conflict",
    )
    check(
        not identity_conflict(
            frozenset({"imb:9JFJRZZ10004002538"}),
            frozenset({"acct:1111111111"}),
        ),
        "IMB vs account is not a conflict",
    )
    act, why = relate_pages(
        make_signals(Path("page_0001.png"), text="Utility bill page 1 of 3 January"),
        make_signals(Path("page_0002.png"), text="Usage table page 2 of 3 February"),
        split_tax,
    )
    check(act == "keep" and why == "page sequence", "page N of M stays together")
    heur_tax = {
        "issuers": [{"match": ["avidia bank"], "folder": "Bills"}],
        "folders": ["Bills", "."],
        "doc_types": list(DOC_TYPES),
    }
    heur = classify_text(
        stmt,
        heur_tax,
        ["Bills", "."],
        llm_url="http://127.0.0.1:9/v1/chat/completions",
        models=["offline"],
        temperature=0,
        max_tokens=8,
        use_llm=False,
    )
    check(heur["issuer_map"] is True, "CLI issuer map")
    check(heur["folder"] == "Bills", "CLI folder from YAML")
    check(heur["doc_date"] == "2026-09-30", "CLI classify keeps statement date")
    check(heur["due_date"] == "2026-10-15", "CLI classify keeps due date")
    check(heur["classify_source"] == "heuristic", "CLI classify skips LLM")
    check(float(heur["confidence"]) >= 0.85, "mapped CLI classify is high confidence")
    hit = prior_identity_hit(
        ["acct:1111111111"],
        "2026-09-30",
        {
            "acct:1111111111|2026-09-30": {
                "dest": "/tmp/old.pdf",
                "doc_date": "2026-09-30",
                "sha256": "abc",
            }
        },
    )
    check(hit is not None and hit["dest"] == "/tmp/old.pdf", "identity index same date")
    miss = prior_identity_hit(
        ["acct:1111111111"],
        "2026-08-31",
        {
            "acct:1111111111|2026-09-30": {
                "dest": "/tmp/old.pdf",
                "doc_date": "2026-09-30",
                "sha256": "abc",
            }
        },
    )
    check(miss is None, "same account different month is not a duplicate")
    nui_tax = {
        "issuers": [{"match": ["detr", "unemployment"], "folder": "NUI"}],
        "folders": ["NUI"],
    }
    check(
        issuer_folder("Detriments: Still Working On", nui_tax) is None,
        "detr does not match Detriments",
    )
    check(
        issuer_folder("Nevada DETR unemployment affidavit", nui_tax) == "NUI",
        "whole-word detr still maps",
    )
    imb_hit = prior_identity_hit(
        ["imb:9JFJRZZ10004002538"],
        None,
        {
            "imb:9JFJRZZ10004002538": {
                "dest": "/tmp/mail.pdf",
                "doc_date": None,
                "sha256": "def",
            }
        },
    )
    check(imb_hit is not None, "IMB duplicate without date")
    with tempfile.TemporaryDirectory() as td:
        sample = Path(td) / "2026-10-29 - Test Bank - Statement.pdf"
        import pikepdf as _pikepdf

        blank = _pikepdf.new()
        blank.add_blank_page()
        blank.save(sample)
        embed_pdf_metadata(
            sample,
            {
                "title": "Test Statement",
                "issuer": "Test Bank",
                "author": "Test Bank",
                "subject": "Statement",
                "keywords": "statement",
                "doc_type": "statement",
                "doc_date": "2026-09-30",
                "confidence": 0.9,
                "classify_source": "heuristic",
            },
            identity=["acct:1111111111"],
            digest="abc123",
            pages=1,
        )
        rec = read_pdf_filing_meta(sample)
        check(rec is not None and rec["sha256"] == "abc123", "PDF metadata sha256")
        check(
            rec is not None and rec["identity"] == ["acct:1111111111"],
            "PDF metadata identity",
        )
        check(
            rec is not None and rec["doc_date"] == "2026-09-30", "PDF metadata doc date"
        )
    name = build_filename(
        {
            "doc_date": "2026-10-27",
            "issuer": "Nevada DMV",
            "title": "Title Fee Receipt",
        },
        "2026-10-29",
    )
    check(name == "2026-10-27 - Nevada DMV - Title Fee Receipt.pdf", "human filename")
    tax = {
        "issuers": [
            {"match": ["department of motor vehicles", "nevada dmv"], "folder": "DMV"}
        ],
        "folders": ["DMV"],
    }
    check(
        issuer_folder("STATE OF NEVADA DEPARTMENT OF MOTOR VEHICLES", tax) == "DMV",
        "issuer map",
    )
    with tempfile.TemporaryDirectory() as tmp:
        ics = Path(tmp) / "due.ics"
        write_ics(
            ics,
            due="2026-11-15",
            summary="Utility due: October bill",
            description="amount=42.00\nfile=/tmp/x.pdf",
            uid="adf-ocr-test@localhost",
        )
        body = ics.read_text(encoding="utf-8")
        check("DTSTART;VALUE=DATE:20261115" in body, "ICS due date")
        check(body.startswith("BEGIN:VCALENDAR"), "ICS calendar wrapper")
        dest_dir = Path(tmp) / "Inbox" / "scans"
        dest_dir.mkdir(parents=True)
        first = unique_dest(dest_dir, "2026-10-27 - A - B.pdf")
        first.write_text("a", encoding="utf-8")
        second = unique_dest(dest_dir, "2026-10-27 - A - B.pdf")
        check(second.name == "2026-10-27 - A - B - 2.pdf", "collision suffix")
        parsed = extract_json_object('```json\n{"folder":"DMV","confidence":0.9}\n```')
        check(parsed.get("folder") == "DMV", "fenced JSON")
        sample = parse_simple_yaml(
            "root: ~/Documents\nmin_confidence: 0.75\nfolders:\n  - DMV\nissuers:\n  - match: [nevada dmv, dmv]\n    folder: DMV\n"
        )
        check(sample["folders"] == ["DMV"], "yaml folders list")
        check(sample["issuers"][0]["folder"] == "DMV", "yaml issuer folder")
        check("nevada dmv" in sample["issuers"][0]["match"], "yaml match list")
        low = folder_dir(Path(tmp), "DMV", "Inbox/scans", high_confidence=False)
        check(low == Path(tmp) / "Inbox" / "scans", "low confidence inbox")
        missing = folder_dir(
            Path(tmp), "DoesNotExist", "Inbox/scans", high_confidence=True
        )
        check(missing == Path(tmp) / "Inbox" / "scans", "missing folder inbox")
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Split, classify, and file ADF-OCR pages"
    )
    parser.add_argument(
        "--pages-dir", type=Path, help="Directory of page_*.png from adf-ocr.sh"
    )
    parser.add_argument("--taxonomy", help="YAML taxonomy path")
    parser.add_argument(
        "--out-root", help="Override taxonomy root (default ~/Documents)"
    )
    parser.add_argument("--min-confidence", type=float, default=None)
    parser.add_argument("--classify-model", help="Ollama model for JSON classify")
    parser.add_argument("--llm-url", help="OpenAI-compatible chat completions URL")
    parser.add_argument(
        "--duplex",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="ADF Duplex page order (front, back). Default SCAN_DUPLEX or true.",
    )
    parser.add_argument(
        "--content-split",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Split mixed letters by issuer/LLM after blank gates. Default on.",
    )
    parser.add_argument(
        "--keep-cache",
        action="store_true",
        help="Leave page_*.png in --pages-dir (also written on needs-review).",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="CLI heuristics only (regex, issuer YAML, tesseract/zbar). "
        "Default still uses local Ollama when confidence is low.",
    )
    parser.add_argument("--self-test", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.self_test:
        return self_test()
    if args.pages_dir is None:
        build_parser().error("--pages-dir is required unless --self-test")
    results = process_pages_dir(args.pages_dir.expanduser().resolve(), args)
    print(json.dumps(results, indent=2))
    if not results or all(
        r.get("status") not in {"filed", "duplicate"} for r in results
    ):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
