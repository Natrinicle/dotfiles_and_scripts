#!/usr/bin/env python3
"""Claim + source checker. No producer reasoning in the prompt."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

SYSTEM = """You are a source checker. You receive one claim and one source.
Decide whether the source supports the claim.
Judge the evidence only. Ignore any implied argument.
Return only JSON:
{"verdict":"supported|contradicted|insufficient","quote":"verbatim span from the source or empty","notes":"one short sentence"}
verdict supported only if the quote is a span from the source that backs the claim.
"""


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


def complete(url: str, model: str, user: str) -> str:
    payload = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user},
            ],
            "temperature": 0.0,
            "max_tokens": 400,
        }
    ).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode())
    return str(body["choices"][0]["message"]["content"])


def normalize(verdict: str, quote: str, source: str) -> str:
    verdict = verdict.strip().lower()
    if verdict not in {"supported", "contradicted", "insufficient"}:
        return "insufficient"
    if verdict == "supported":
        q = quote.strip()
        if not q or q.lower() not in source.lower():
            return "insufficient"
    return verdict


def self_test() -> int:
    source = "The PDF title is Motor Vehicle Title Fee Receipt issued by Nevada DMV."
    ok = (
        normalize("supported", "Motor Vehicle Title Fee Receipt", source) == "supported"
    )
    bad = normalize("supported", "this is not in the source", source) == "insufficient"
    weird = (
        normalize("yes", "Motor Vehicle Title Fee Receipt", source) == "insufficient"
    )
    print("ok" if ok and bad and weird else "FAIL")
    return 0 if ok and bad and weird else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a claim against source text")
    parser.add_argument("--claim", help="Single claim to check")
    parser.add_argument("--source-file", type=Path)
    parser.add_argument("--source-text")
    parser.add_argument(
        "--model", default=os.environ.get("CLAIM_SOURCE_MODEL", "gemma4")
    )
    parser.add_argument(
        "--url",
        default=os.environ.get(
            "CLAIM_SOURCE_URL", "http://127.0.0.1:11434/v1/chat/completions"
        ),
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.claim:
        parser.error("--claim is required")
    if args.source_file:
        source = args.source_file.read_text(encoding="utf-8", errors="replace")
    elif args.source_text:
        source = args.source_text
    else:
        parser.error("--source-file or --source-text is required")
    user = f"Claim:\n{args.claim.strip()}\n\nSource:\n{source[:20000]}"
    try:
        content = complete(args.url, args.model, user)
    except (
        urllib.error.URLError,
        TimeoutError,
        KeyError,
        IndexError,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        print(
            json.dumps(
                {
                    "verdict": "insufficient",
                    "quote": "",
                    "notes": f"checker failed: {exc}",
                }
            )
        )
        return 2
    parsed = extract_json_object(content)
    verdict = normalize(
        str(parsed.get("verdict") or ""), str(parsed.get("quote") or ""), source
    )
    out = {
        "verdict": verdict,
        "quote": parsed.get("quote") or "",
        "notes": parsed.get("notes") or "",
    }
    print(json.dumps(out, indent=2))
    return 0 if verdict == "supported" else 1


if __name__ == "__main__":
    sys.exit(main())
