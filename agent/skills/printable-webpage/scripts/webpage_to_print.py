#!/usr/bin/env python3
"""Fetch a webpage, strip chrome, and emit a compact printable PDF."""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Comment

from extract_core import (
    CHROME_TEXT_RE,
    JUNK_RE,
    bundle_finale,
    compact_howto,
    download_images,
    drop_duplicate_intro,
    extract_blocks,
    extract_comments,
    fetch_html,
    intro_from_blocks,
    pair_short_labels,
    page_title,
    pick_container,
    site_name,
    skill_root,
    split_reader_comments,
    strip_chrome,
)
from print_layout import chrome_print, load_from_json, render_html, weak_extraction


def main() -> int:
    p = argparse.ArgumentParser(description="Convert a webpage into a compact printable PDF")
    p.add_argument("--url")
    p.add_argument("--from-json")
    p.add_argument("--out", required=True, help="Output PDF path")
    p.add_argument("--html-out", help="Also write the print HTML")
    p.add_argument("--comments", action="store_true", help="Include comments (off by default)")
    p.add_argument("--page-size", default="letter", choices=["letter", "a4"])
    p.add_argument("--columns", type=int, default=0, help="1, 2, 3, or 0=auto")
    p.add_argument("--keep-work", action="store_true", help="Do not delete temp image dir")
    args = p.parse_args()

    if not args.url and not args.from_json:
        p.error("provide --url or --from-json")

    css = (skill_root() / "assets" / "print.css").read_text()
    work = Path(tempfile.mkdtemp(prefix="printable-"))
    comments: list[dict[str, str]] = []

    try:
        if args.from_json:
            data = load_from_json(Path(args.from_json))
            url = data.get("url") or args.url or ""
            title = data.get("title") or url
            site = data.get("site") or (urlparse(url).hostname or "")
            blocks = data.get("blocks") or []
            comments = data.get("comments") or []
            intro = data.get("intro")
            if isinstance(intro, str):
                intro_list = [intro] if intro else []
            elif isinstance(intro, list):
                intro_list = intro
            else:
                intro_list, blocks = intro_from_blocks(blocks)
        else:
            html_text, final_url = fetch_html(args.url)
            soup = BeautifulSoup(html_text, "lxml")
            for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
                comment.extract()
            strip_chrome(soup)
            title = page_title(soup, final_url)
            site = site_name(soup, final_url)
            container = pick_container(soup)
            blocks = extract_blocks(container, final_url)
            blocks = [
                b
                for b in blocks
                if not (
                    b.get("text")
                    and (CHROME_TEXT_RE.search(b["text"]) or JUNK_RE.search(b["text"]))
                    and len(b.get("text") or "") < 500
                )
            ]
            blocks = pair_short_labels(blocks)
            intro_list, blocks = intro_from_blocks(blocks)
            intro_list, blocks = drop_duplicate_intro(intro_list, blocks)
            if not intro_list:
                ogd = soup.find("meta", attrs={"property": "og:description"}) or soup.find(
                    "meta", attrs={"name": "description"}
                )
                if ogd and ogd.get("content"):
                    intro_list = [ogd["content"].strip()]
            url = final_url
            reader_comments: list[dict[str, str]] = []
            blocks, reader_comments = split_reader_comments(blocks)
            widget_comments = extract_comments(BeautifulSoup(html_text, "lxml")) if args.comments else []
            comments = reader_comments + widget_comments

        blocks = pair_short_labels(blocks)
        blocks = bundle_finale(blocks)
        blocks = compact_howto(blocks)
        intro_list, blocks = drop_duplicate_intro(intro_list, blocks)
        if not args.comments:
            comments = []

        download_images(blocks, work / "img")
        for b in blocks:
            figs = [b] if b.get("type") == "figure" else (b.get("images") or [])
            for fig in figs:
                local = fig.get("local")
                if local:
                    pth = Path(local)
                    if not pth.exists() and pth.with_suffix(".jpg").exists():
                        fig["local"] = str(pth.with_suffix(".jpg"))

        html_doc = render_html(
            title=title,
            url=url,
            site=site,
            intro=intro_list,
            blocks=blocks,
            comments=comments,
            page_size=args.page_size,
            css=css,
            columns=args.columns,
        )
        html_path = Path(args.html_out) if args.html_out else work / "print.html"
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(html_doc, encoding="utf-8")

        out = Path(args.out)
        chrome_print(html_path, out)

        figs = sum(1 for b in blocks if b["type"] == "figure")
        steps = sum(1 for b in blocks if b["type"] == "step")
        step_imgs = sum(len(b.get("images") or []) for b in blocks if b["type"] == "step")
        kept_imgs = 0
        for b in blocks:
            if b.get("type") == "figure" and b.get("local"):
                kept_imgs += 1
            if b.get("type") == "step":
                kept_imgs += sum(1 for im in b.get("images") or [] if im.get("local"))

        print(f"Wrote {out} ({out.stat().st_size} bytes)")
        print(f"title: {title}")
        print(f"url: {url}")
        print(f"blocks: {len(blocks)} steps={steps} figures={figs} step_images={step_imgs} downloaded={kept_imgs}")
        print(f"comments: {len(comments)}")
        print(f"html: {html_path}")
        if weak_extraction(blocks, title, site):
            print("WARN: weak extraction — consider --from-json via browser-extract.js")
            return 2
        return 0
    finally:
        if not args.keep_work:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
