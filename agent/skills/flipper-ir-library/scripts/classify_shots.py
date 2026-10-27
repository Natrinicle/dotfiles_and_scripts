#!/usr/bin/env python3
"""Classify camera originals in a unit folder with local Ollama vision.

Usage:
  classify_shots.py DIR [--model gemma4] [--url http://127.0.0.1:11434]

Prints JSON lines to stdout. Images stay on this machine. Use this to route
remote / unit / label / manual / skip before a rembg cutout, instead of a
cloud vision call.

Kinds:
  remote  handheld IR clicker
  unit    the device itself (lamp, bulb, player, cassette)
  label   tight rating-plate / spec-table crop
  manual  included user-manual / instruction / packing-list page
  skip    in-use install, lifestyle, duplicate, unusable, or not a pack shot
"""

from __future__ import annotations

import argparse
import base64
import fnmatch
import io
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image, ImageOps

KINDS = ("remote", "unit", "label", "manual", "skip")
PROMPT = """Classify this product-pack photograph. Reply with JSON only:
{"kind":"remote|unit|label|manual|skip","reason":"short"}

kind meanings:
- remote: a physical handheld IR clicker filling most of the frame (real plastic buttons), not a drawing of a remote
- unit: the physical device as hardware (lamp housing, bulb, panel, player). Not a printed picture of it.
- label: close crop of a rating plate, spec table, or ID sticker
- manual: a paper leaflet, owner's manual, instruction sheet, or packing list. Paper with a printed lamp or bulb is still manual.
- skip: hardware mounted in use (wall, RV, ceiling), lifestyle, or a whole-kit table layout

Prefer manual over unit when the subject is an open booklet or printed page.
Prefer skip when the hardware is installed on a building or vehicle.

Do not transcribe serials. Do not invent a brand."""


def _jpeg_b64(path: Path, long_edge: int) -> str:
    im = Image.open(path)
    im = ImageOps.exif_transpose(im)
    im = im.convert("RGB")
    w, h = im.size
    m = max(w, h)
    if m > long_edge:
        scale = long_edge / m
        im = im.resize(
            (max(1, round(w * scale)), max(1, round(h * scale))),
            Image.Resampling.LANCZOS,
        )
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=70, optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _generate(
    url: str,
    model: str,
    image_b64: str,
    timeout: int,
) -> dict:
    # /api/chat with images hung on gemma4 (8B, 4k ctx). /api/generate returns.
    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "prompt": PROMPT,
        "images": [image_b64],
        "keep_alive": "30m",
        "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 96},
    }
    req = urllib.request.Request(
        url.rstrip("/") + "/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    content = body.get("response", "")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {"kind": "skip", "reason": f"non-json: {content[:200]}"}
    kind = str(parsed.get("kind", "skip")).strip().lower()
    if kind not in KINDS:
        kind = "skip"
    reason = str(parsed.get("reason", "")).strip()
    return {"kind": kind, "reason": reason}


def _iter_shots(root: Path) -> list[Path]:
    shots: list[Path] = []
    for path in sorted(root.iterdir()):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".heic"}:
            continue
        shots.append(path)
    return shots


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("dir", type=Path)
    p.add_argument("--model", default="gemma4")
    p.add_argument("--url", default="http://127.0.0.1:11434")
    p.add_argument("--long-edge", type=int, default=512)
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument(
        "--pattern",
        default="*.ignore.*",
        help="glob of files to classify (default: camera originals)",
    )
    args = p.parse_args()
    root = args.dir.expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"not a directory: {root}")
    shots = _iter_shots(root)
    if args.pattern:
        shots = [path for path in shots if fnmatch.fnmatch(path.name, args.pattern)]
    if not shots:
        raise SystemExit(f"no images matching {args.pattern} in {root}")
    for path in shots:
        try:
            b64 = _jpeg_b64(path, args.long_edge)
            result = _generate(args.url, args.model, b64, args.timeout)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            result = {"kind": "skip", "reason": f"ollama error: {exc}"}
        rec = {"path": str(path), "name": path.name, **result}
        print(json.dumps(rec), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
