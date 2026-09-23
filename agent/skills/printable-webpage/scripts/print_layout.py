#!/usr/bin/env python3
"""HTML/PDF layout for printable-webpage."""
from __future__ import annotations

import html
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

from extract_core import file_to_data_uri, find_chrome


def detect_how_to(blocks: list[dict[str, Any]]) -> bool:
    steps = sum(1 for b in blocks if b.get("type") == "step")
    figs = sum(1 for b in blocks if b.get("type") == "figure")
    step_figs = sum(len(b.get("images") or []) for b in blocks if b.get("type") == "step")
    paras = sum(1 for b in blocks if b.get("type") == "para")
    return steps >= 3 or (figs + step_figs >= 6 and paras <= 3)


def render_html(
    *,
    title: str,
    url: str,
    site: str,
    intro: list[str],
    blocks: list[dict[str, Any]],
    comments: list[dict[str, str]] | None,
    page_size: str,
    css: str,
    columns: int,
) -> str:
    how_to = detect_how_to(blocks)
    cols = columns if columns else (2 if how_to else 1)

    def esc(s: str) -> str:
        return html.escape(s or "")

    def img_tag(fig: dict[str, Any]) -> str:
        local = fig.get("local")
        src = fig.get("src") or ""
        alt = esc(fig.get("alt") or fig.get("caption") or "")
        if local and Path(local).exists():
            src = file_to_data_uri(local)
        if not src:
            return ""
        return f'<div class="photo"><img src="{src}" alt="{alt}"></div>'

    parts: list[str] = []
    parts.append("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>")
    parts.append(f"<title>{esc(title)}</title>")
    css_out = css.replace("size: letter;", f"size: {page_size};")
    parts.append(f"<style>{css_out}</style></head><body>")
    parts.append("<header class='masthead'>")
    parts.append(f"<h1>{esc(title)}</h1>")
    parts.append("<div class='meta'>")
    parts.append(f"<div>Source — <a href='{esc(url)}'>{esc(url)}</a></div>")
    extra = []
    if site:
        extra.append(esc(site))
    extra.append(date.today().isoformat())
    parts.append(f"<div>{' · '.join(extra)}</div>")
    parts.append("</div></header>")
    if intro:
        parts.append("<section class='intro'>")
        for p in intro:
            parts.append(f"<p>{esc(p)}</p>")
        parts.append("</section>")
    if how_to:
        parts.append(f"<section class='grid cols-{cols}'>")
        for b in blocks:
            if b["type"] == "step":
                imgs = [im for im in (b.get("images") or []) if im.get("local") or im.get("src")]
                parts.append("<article class='card'>")
                if b.get("label"):
                    parts.append(f"<div class='step-label'>{esc(b['label'])}</div>")
                if not imgs:
                    parts.append(f"<p class='caption'>{esc(b.get('text') or '')}</p>")
                elif len(imgs) == 1:
                    parts.append(img_tag(imgs[0]))
                    if b.get("text"):
                        parts.append(f"<p class='caption'>{esc(b.get('text') or '')}</p>")
                else:
                    parts.append("<div class='img-row'>")
                    for fig in imgs[:3]:
                        parts.append(img_tag(fig))
                    parts.append("</div>")
                    if b.get("text"):
                        parts.append(f"<p class='caption'>{esc(b.get('text') or '')}</p>")
                parts.append("</article>")
            elif b["type"] == "figure":
                cap = b.get("caption") or b.get("alt") or ""
                parts.append("<article class='card'>")
                parts.append(img_tag(b))
                if cap:
                    parts.append(f"<p class='caption'>{esc(cap)}</p>")
                parts.append("</article>")
            elif b["type"] == "heading":
                parts.append(f"<article class='card span'><p class='caption'><strong>{esc(b['text'])}</strong></p></article>")
            elif b["type"] == "para":
                parts.append(f"<article class='card span'><p class='caption'>{esc(b['text'])}</p></article>")
        parts.append("</section>")
    else:
        parts.append("<section class='prose'>")
        for b in blocks:
            if b["type"] == "heading":
                parts.append(f"<h2>{esc(b['text'])}</h2>")
            elif b["type"] == "para":
                parts.append(f"<p>{esc(b['text'])}</p>")
            elif b["type"] == "figure":
                cap = b.get("caption") or b.get("alt") or ""
                parts.append("<figure>")
                parts.append(img_tag(b))
                if cap:
                    parts.append(f"<figcaption>{esc(cap)}</figcaption>")
                parts.append("</figure>")
            elif b["type"] == "step":
                parts.append(f"<h2>{esc(b.get('label') or 'Step')}</h2>")
                parts.append(f"<p>{esc(b.get('text') or '')}</p>")
                for fig in b.get("images") or []:
                    parts.append("<figure>")
                    parts.append(img_tag(fig))
                    parts.append("</figure>")
        parts.append("</section>")
    if comments:
        parts.append("<section class='comments'><h2>Comments</h2>")
        for c in comments:
            parts.append("<div class='comment'>")
            if c.get("author"):
                parts.append(f"<div class='who'>{esc(c['author'])}</div>")
            parts.append(f"<div>{esc(c.get('text') or '')}</div>")
            parts.append("</div>")
        parts.append("</section>")
    parts.append(
        "<p class='footer-note'>Printer-friendly extract. Layout generated locally; "
        "images and wording remain copyright of the source site.</p>"
    )
    parts.append("</body></html>")
    return "\n".join(parts)


def chrome_print(html_path: Path, pdf_path: Path) -> None:
    chrome = find_chrome()
    if not chrome:
        raise SystemExit("google-chrome / chromium not found")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--allow-file-access-from-files",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        html_path.as_uri(),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    if proc.returncode != 0 or not pdf_path.exists() or pdf_path.stat().st_size < 200:
        raise SystemExit(f"Chrome print failed (code {proc.returncode}): {proc.stderr[-800:]}")


def weak_extraction(blocks: list[dict[str, Any]], title: str, site: str) -> bool:
    figs = sum(1 for b in blocks if b["type"] == "figure")
    step_imgs = sum(len(b.get("images") or []) for b in blocks if b["type"] == "step")
    paras = sum(1 for b in blocks if b["type"] in {"para", "step"})
    if paras < 2 and (figs + step_imgs) < 2:
        return True
    if title and site and title.lower() == site.lower():
        return True
    return False


def load_from_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if "blocks" not in data:
        raise SystemExit("--from-json file missing 'blocks'")
    return data
