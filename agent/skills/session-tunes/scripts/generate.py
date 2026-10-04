#!/usr/bin/env python3
"""Mint original RTTTL on local Ollama (no upstream tokens)."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from config import USER_LIB, load_config
from rtttl import extract_rtttl_line, parse_rtttl

KINDS = ("busy", "alert", "error")

_PROMPTS = {
    "busy": (
        "peppy upbeat major/pentatonic bounce, a unique motif (never a famous tune). "
        "Keep it light, not frantic. Vary rhythm."
    ),
    "alert": (
        "short sharper staccato sting meaning the user must look at the session. "
        "Higher notes, rests between hits, under 4 seconds."
    ),
    "error": (
        "short descending original sting meaning a failure. "
        "Not a siren. Under 4 seconds."
    ),
}


def _prompt(kind: str) -> str:
    return (
        "Write one original Nokia RTTTL ringtone on a single line.\n"
        "Format: Name:d=8,o=5,b=160:note,note,note\n"
        "Rules:\n"
        "- Original composition only. No copyrighted or famous melodies.\n"
        f"- Mood: {_PROMPTS[kind]}\n"
        "- 8 to 28 notes. About 2 to 8 seconds long.\n"
        "- Note tokens like 8c6, 16e, 4g, p, 8d#, 8a5. Octaves 5-7.\n"
        "- Duration letters d=4|8|16, octave o=5|6, bpm b=120-220.\n"
        "- Reply with ONLY the RTTTL line, no markdown.\n"
        "Example: BusyHop:d=8,o=5,b=160:c6,e,g,e,c6,g,e,c,d,f,a,f,d6,a\n"
    )


def _ollama_generate(url: str, model: str, prompt: str) -> str:
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.9, "num_predict": 192},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url.rstrip("/") + "/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return str(body.get("response") or "")


def mint_rtttl(kind: str = "busy") -> Path:
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    cfg = load_config()
    last_err = "no attempt"
    for _attempt in range(3):
        try:
            text = _ollama_generate(
                cfg["ollama_url"], cfg["ollama_model"], _prompt(kind)
            )
            line = extract_rtttl_line(text)
            tune = parse_rtttl(line)
        except (
            ValueError,
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
            OSError,
        ) as exc:
            last_err = str(exc)
            continue
        n = len(tune.notes)
        if n < 6 or n > 40:
            last_err = f"note count {n}"
            continue
        if not (2.0 <= tune.duration_s <= 12.0):
            last_err = f"duration {tune.duration_s:.2f}s"
            continue
        USER_LIB.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        path = USER_LIB / f"{kind}-{stamp}.rtttl"
        path.write_text(line.strip() + "\n", encoding="utf-8")
        return path
    raise RuntimeError(f"ollama did not return valid RTTTL ({last_err})")


def main() -> int:
    kind = sys.argv[1] if len(sys.argv) > 1 else "busy"
    try:
        path = mint_rtttl(kind)
    except Exception as exc:  # noqa: BLE001 — CLI surface
        print(f"generate failed: {exc}", file=sys.stderr)
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
