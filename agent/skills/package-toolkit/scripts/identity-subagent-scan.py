#!/usr/bin/env python3
"""Build a leftover-identity bundle for a local (lower-level) subagent.

Walks the pack the same way residual-identity-scan does, extracts heuristic
candidates, and writes a short bundle. The parent then spawns a local
subagent with references/identity-subagent-prompt.md.

Usage:
  identity-subagent-scan.py [--root DIR] [--out FILE] [--max-hits N]
  identity-subagent-scan.py --root DIR --include-code   # also scan .py/.json
  identity-subagent-scan.py --root DIR --ollama         # classify via local gemma4
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from identity_candidates import (
    extract_text_candidates,
    format_bundle,
    is_prose_file,
    load_vendor_names,
    should_skip_pack_file,
)
from identity_denylist import in_ci

PROMPT_FILE = (
    Path(__file__).resolve().parent.parent
    / "references"
    / "identity-subagent-prompt.md"
)


def _load_scan_mod():
    path = Path(__file__).resolve().parent / "residual-identity-scan.py"
    spec = importlib.util.spec_from_file_location("_residual_identity_scan", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def extract_json_object(text: str) -> str:
    """Return pretty JSON from model text, or the original text."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end <= start:
        return text
    blob = stripped[start : end + 1]
    try:
        obj = json.loads(blob)
    except json.JSONDecodeError:
        return text
    return json.dumps(obj, indent=2)


def classify_with_ollama(bundle: str) -> str:
    prompt_text = ""
    if PROMPT_FILE.is_file():
        prompt_text = PROMPT_FILE.read_text(encoding="utf-8")
    model = os.environ.get("IDENTITY_SUBAGENT_MODEL", "gemma4")
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    if not host.startswith("http"):
        host = "http://" + host
    timeout = float(os.environ.get("IDENTITY_SUBAGENT_TIMEOUT", "180"))
    payload = {
        "model": model,
        "prompt": (
            prompt_text + "\n\nBUNDLE:\n" + bundle + "\nReturn only the JSON object.\n"
        ),
        "stream": False,
        "think": False,
        "options": {"temperature": 0.1, "num_predict": 1024},
    }
    req = urllib.request.Request(
        host + "/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(
            f"identity-subagent-scan: ollama HTTP {exc.code}: {detail}"
        ) from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise SystemExit(f"identity-subagent-scan: ollama failed: {exc}") from exc
    response = str(body.get("response") or "").strip()
    if not response:
        response = str(body.get("thinking") or "").strip()
    if not response:
        reason = body.get("done_reason", "unknown")
        raise SystemExit(
            f"identity-subagent-scan: ollama returned empty response ({reason})"
        )
    return extract_json_object(response)


def collect_rows(
    root: Path, max_hits: int, *, include_code: bool
) -> list[tuple[str, int, str, str]]:
    scan = _load_scan_mod()
    vendor = load_vendor_names()
    rows: list[tuple[str, int, str, str]] = []
    for path in scan.iter_files(root, []):
        if scan.should_skip_file(path, root) or should_skip_pack_file(path, root):
            continue
        if not include_code and not is_prose_file(path):
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if b"\0" in data[:2048]:
            continue
        text = data.decode("utf-8", errors="replace")
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            rel = str(path)
        for lineno, span, line in extract_text_candidates(text, vendor):
            rows.append((rel, lineno, span, line))
            if len(rows) >= max_hits:
                return rows
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--max-hits", type=int, default=100)
    parser.add_argument(
        "--include-code",
        action="store_true",
        help="Also scan .py/.json (noisy; default is prose only)",
    )
    parser.add_argument(
        "--print-prompt",
        action="store_true",
        help="Print the subagent prompt path and exit",
    )
    parser.add_argument(
        "--ollama",
        action="store_true",
        help="Classify the bundle with local Ollama gemma4 (/api/generate)",
    )
    args = parser.parse_args(argv)

    if args.print_prompt:
        print(PROMPT_FILE)
        return 0

    if in_ci():
        if args.ollama:
            print(
                "identity-subagent-scan: skip --ollama in CI "
                "(heuristic bundle still available via --out)",
                file=sys.stderr,
            )
            args.ollama = False
        elif not args.out:
            print(
                "identity-subagent-scan: skip spawn in CI "
                "(heuristic bundle still available via --out)",
                file=sys.stderr,
            )

    root = (args.root or Path.cwd()).resolve()
    rows = collect_rows(root, max(1, args.max_hits), include_code=args.include_code)
    bundle = format_bundle(rows, max_hits=args.max_hits)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(bundle, encoding="utf-8")
        print(
            f"identity-subagent-scan: wrote {args.out} ({len(rows)} candidates)",
            file=sys.stderr,
        )
    elif not args.ollama:
        sys.stdout.write(bundle)
    print(
        f"identity-subagent-scan: {len(rows)} heuristic candidates. "
        f"Classify with --ollama or a local-extract child plus {PROMPT_FILE.name}.",
        file=sys.stderr,
    )
    if args.ollama:
        if not rows:
            print('{\n  "hits": [],\n  "kept_vendor": []\n}')
        else:
            print(classify_with_ollama(bundle))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
