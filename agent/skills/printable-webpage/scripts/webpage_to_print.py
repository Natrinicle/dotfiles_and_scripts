#!/usr/bin/env python3
"""Fetch a webpage, strip chrome, and emit a compact printable PDF."""
from __future__ import annotations
import argparse, base64, hashlib, html, json, mimetypes, re, shutil, subprocess, sys, tempfile
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from PIL import Image
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
TIMEOUT = 25
MAX_HTML_BYTES = 8 * 1024 * 1024
MAX_IMAGE_BYTES = 6 * 1024 * 1024
MAX_IMAGES = 40
DROP_RE = re.compile(r"nav|menu|sidebar|advert|adsbygoogle|cookie|social|share|related|popular|recommend|subscribe|newsletter|popup|modal|breadcrumb|translate|sitenav|header-wrap|footer", re.I)
DROP_TAGS = {"script","style","noscript","iframe","form","button","input","select","textarea","nav","footer","aside","svg"}
AD_HOST_RE = re.compile(r"doubleclick|googlesyndication|googleadservices|adsystem|facebook\\.com/tr|scorecardresearch|quantserve|outbrain|taboola", re.I)
PIXEL_RE = re.compile(r"cleardot|pixel|1x1|poweredby|sprite|\\bicon\\b|\\blogo\\b", re.I)
STEP_RE = re.compile(r"\\bstep\\s*(\\d+)\\b", re.I)
CTA_RE = re.compile(r"(comment and submit|submit your photo|comment box at the end|share this|like origami\\?|tell your friends|discover more|order diy|search this site|custom search|login with your (facebook|twitter|google|yahoo)|you can login with)", re.I)
JUNK_RE = re.compile(r"Instance(Begin|End)Editable|name=\"content\\d*\"|//\\s*<!\\[CDATA\\[", re.I)
COMMENT_FROM_RE = re.compile(r"^From\\s+.+\\s+(in|of)\\s+", re.I)
DONE_RE = re.compile(r"(this is your|finished|you'?re done|completed)", re.I)
def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent
def fetch_html(url: str) -> tuple[str, str]:
    r = requests.get(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"}, timeout=TIMEOUT, allow_redirects=True)
    r.raise_for_status()
    if len(r.content) > MAX_HTML_BYTES:
        raise SystemExit(f"HTML too large ({len(r.content)} bytes)")
    r.encoding = r.apparent_encoding or r.encoding or "utf-8"
    return r.text, r.url
def _hay(el: Tag) -> str:
    attrs = el.attrs or {}
    raw_id = attrs.get("id") or ""
    cid = " ".join(raw_id) if isinstance(raw_id, list) else str(raw_id)
    return f"{cid} {' '.join(attrs.get('class') or [])} {attrs.get('role') or ''}"
def strip_chrome(soup: BeautifulSoup) -> None:
    for tag in list(soup.find_all(True)):
        if not isinstance(tag, Tag) or tag.attrs is None or tag.name is None:
            continue
        name = tag.name.lower()
        if name in DROP_TAGS:
            tag.decompose(); continue
        role = str((tag.attrs or {}).get("role") or "").lower()
        if role in {"navigation", "banner", "complementary", "contentinfo", "search"}:
            tag.decompose(); continue
        try:
            hay = _hay(tag)
        except Exception:
            continue
        if DROP_RE.search(hay) and name not in {"article", "main", "body", "html"}:
            tag.decompose()
def _text_len(el: Tag) -> int:
    return len(el.get_text(" ", strip=True) or "")
def _link_chars(el: Tag) -> int:
    return sum(len(a.get_text(" ", strip=True) or "") for a in el.find_all("a"))
def score_container(el: Tag) -> float:
    text = _text_len(el)
    if text < 40:
        return 0.0
    imgs = sum(1 for img in el.find_all("img") if not PIXEL_RE.search(img.get("src") or ""))
    paras = len(el.find_all("p"))
    links = _link_chars(el)
    score = text + 400 * imgs + 80 * paras - 3 * links
    if links / max(text, 1) > 0.55 and imgs < 3:
        score *= 0.15
    return score
def pick_container(soup: BeautifulSoup) -> Tag:
    body = soup.body or soup
    candidates: list[Tag] = []
    for sel in ("article", "main", "[role=main]", "#content", "#main", ".post", ".entry-content", ".entry", ".post-content", "#mainContent"):
        candidates.extend(body.select(sel))
    for child in body.find_all(["div", "td", "section"], recursive=True):
        if _text_len(child) > 200:
            candidates.append(child)
    best, best_score, seen = body, score_container(body) * 0.4, set()
    for el in candidates:
        if id(el) in seen:
            continue
        seen.add(id(el))
        s = score_container(el)
        if s > best_score:
            best, best_score = el, s
    return best
def page_title(soup: BeautifulSoup, fallback: str) -> str:
    h1 = soup.find("h1")
    if h1:
        t = h1.get_text(" ", strip=True)
        if t and len(t) < 200:
            return t
    og = soup.find("meta", attrs={"property": "og:title"})
    if og and og.get("content"):
        return og["content"].strip()
    if soup.title and soup.title.string:
        raw = re.split(r"\s+[|\-\u2013\u2014]\s+", soup.title.string.strip())[0].strip()
        if raw:
            return raw
    return fallback
def site_name(soup: BeautifulSoup, url: str) -> str:
    og = soup.find("meta", attrs={"property": "og:site_name"})
    if og and og.get("content"):
        return og["content"].strip()
    return (urlparse(url).hostname or "").removeprefix("www.")
def abs_url(src: str, base: str) -> str | None:
    if not src:
        return None
    src = src.strip()
    if src.startswith("data:"):
        return src
    if src.startswith("//"):
        src = "https:" + src
    return urljoin(base, src)
def img_candidates(img: Tag, base: str) -> list[str]:
    urls: list[str] = []
    srcset = img.get("srcset") or img.get("data-srcset") or ""
    if srcset:
        urls.extend(reversed([chunk.strip().split()[0] for chunk in srcset.split(",") if chunk.strip().split()]))
    for attr in ("src", "data-src", "data-original", "data-lazy-src"):
        if img.get(attr):
            urls.append(img.get(attr))
    out, seen = [], set()
    for u in urls:
        au = abs_url(u, base)
        if au and au not in seen:
            seen.add(au); out.append(au)
            if "/thumbnails/" in au:
                sib = au.replace("/thumbnails/", "/")
                if sib not in seen:
                    out.append(sib)
    return out
def looks_tiny(img: Tag) -> bool:
    def dim(val: Any) -> int:
        try:
            return int(re.sub(r"[^\d]", "", str(val or "0")) or 0)
        except ValueError:
            return 0
    w, h = dim(img.get("width")), dim(img.get("height"))
    return bool(w and h and w < 80 and h < 80)
def extract_blocks(container: Tag, base: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    seen_img: set[str] = set()
    def add_para(text: str) -> None:
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return
        if CTA_RE.search(text) and len(text) < 240:
            return
        if JUNK_RE.search(text):
            text = re.sub(r"\s+", " ", JUNK_RE.sub(" ", text)).strip()
            if len(text) < 40:
                return
        if re.fullmatch(r"(search this site|custom search|translate this site|select language.*)", text, re.I):
            return
        blocks.append({"type": "para", "text": text})
    def add_img(img: Tag) -> None:
        if looks_tiny(img):
            return
        urls = img_candidates(img, base)
        if not urls:
            return
        primary = urls[0]
        if PIXEL_RE.search(primary) or AD_HOST_RE.search(urlparse(primary).hostname or "") or primary in seen_img:
            return
        seen_img.add(primary)
        alt = (img.get("alt") or "").strip()
        blocks.append({"type": "figure", "src": primary, "altsrc": urls[1:], "alt": alt, "caption": alt})
    def walk(node: Tag | NavigableString) -> None:
        if not isinstance(node, Tag):
            return
        name = node.name.lower()
        if name in DROP_TAGS:
            return
        if name in {"h1","h2","h3","h4","h5","h6"}:
            text = node.get_text(" ", strip=True)
            if text:
                blocks.append({"type": "heading", "text": text, "level": int(name[1])})
            return
        if name == "p":
            for img in node.find_all("img"):
                add_img(img)
            add_para(node.get_text(" ", strip=True)); return
        if name == "img":
            add_img(node); return
        if name in {"ul","ol"}:
            for li in node.find_all("li", recursive=False):
                for img in li.find_all("img"):
                    add_img(img)
                t = li.get_text(" ", strip=True)
                if t:
                    add_para("\u2022 " + t)
            return
        if name == "br":
            return
        pending: list[str] = []
        for child in list(node.children):
            if isinstance(child, NavigableString):
                t = str(child).strip()
                if t:
                    pending.append(t)
                continue
            if pending:
                blob = " ".join(pending); pending = []
                if len(blob) > 40:
                    add_para(blob)
            walk(child)
        if pending:
            blob = " ".join(pending)
            if len(blob) > 40:
                add_para(blob)
    walk(container)
    return coalesce_steps(blocks)
def tidy_step_text(text: str, label: str | None) -> str:
    if not text:
        return text
    if label:
        text = re.sub(rf"^{re.escape(label)}\s*[:.-]\s*", "", text, flags=re.I)
        text = re.sub(r"^Step\s+\d+\s*[:.-]\s*", "", text, flags=re.I)
    return text.strip()
def coalesce_steps(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []; i = 0
    while i < len(blocks):
        b = blocks[i]
        if b["type"] in {"para", "heading"} and STEP_RE.search(b.get("text") or ""):
            step = {"type": "step", "text": b["text"], "images": [], "label": None}
            m = STEP_RE.search(b["text"])
            if m:
                step["label"] = f"Step {m.group(1)}"
            step["text"] = tidy_step_text(step["text"], step["label"])
            j = i + 1
            while j < len(blocks) and blocks[j]["type"] == "figure":
                step["images"].append(blocks[j]); j += 1
            if out and out[-1]["type"] == "figure" and not step["images"]:
                step["images"].append(out.pop())
            out.append(step); i = j; continue
        out.append(b); i += 1
    return out
def extract_comments(soup: BeautifulSoup) -> list[dict[str, str]]:
    root = soup.select_one("#comments, .comments, .comment-list, #disqus_thread, #comment-wrap")
    if not root:
        return []
    items = root.select(".comment, .comment-body, li.comment, article") or [p for p in root.find_all("p") if _text_len(p) > 20]
    comments = []
    for item in items:
        text = item.get_text(" ", strip=True)
        if len(text) < 8 or len(text) > 2000:
            continue
        who_el = item.select_one(".fn, .author, .comment-author, cite")
        comments.append({"author": who_el.get_text(" ", strip=True) if who_el else "", "text": text[:1200]})
        if len(comments) >= 40:
            break
    return comments
def split_reader_comments(blocks: list[dict[str, Any]]):
    cut = None
    for i, b in enumerate(blocks):
        if b["type"] in {"para", "heading"} and COMMENT_FROM_RE.search(b.get("text") or ""):
            prior_steps = sum(1 for x in blocks[:i] if x.get("type") == "step")
            prior_done = any(DONE_RE.search(x.get("text") or "") for x in blocks[:i])
            if prior_steps >= 3 or prior_done or i > 8:
                cut = i; break
    if cut is None:
        return blocks, []
    main, tail, comments, pending_author = blocks[:cut], blocks[cut:], [], ""
    for b in tail:
        if b["type"] in {"para", "heading"}:
            t = b.get("text") or ""
            if COMMENT_FROM_RE.match(t):
                pending_author = t.split(":")[0].replace("From ", "", 1).strip()
                comments.append({"author": pending_author, "text": t})
            elif comments:
                comments[-1]["text"] = (comments[-1]["text"] + " " + t).strip()
            else:
                comments.append({"author": pending_author, "text": t})
        elif b["type"] == "figure":
            comments.append({"author": pending_author, "text": b.get("caption") or b.get("alt") or "(reader photo)"})
    return main, comments
def pair_short_labels(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out, i = [], 0
    while i < len(blocks):
        b, nxt = blocks[i], blocks[i+1] if i+1 < len(blocks) else None
        if b["type"] == "para" and nxt and nxt["type"] == "figure" and len(b.get("text") or "") <= 40:
            nxt = dict(nxt); nxt["caption"] = b["text"].rstrip(":"); nxt["alt"] = nxt.get("alt") or b["text"]
            out.append(nxt); i += 2; continue
        out.append(b); i += 1
    return out
def intro_from_blocks(blocks: list[dict[str, Any]]):
    intro, rest, started = [], [], False
    for b in blocks:
        if not started:
            if b["type"] == "heading" and b.get("level", 2) == 1:
                continue
            if b["type"] == "para" and len(intro) < 3 and len(b["text"]) > 40:
                intro.append(b["text"]); continue
            started = True
        rest.append(b)
    return intro, rest
def hashed_name(url: str, data: bytes) -> str:
    digest = hashlib.sha1(url.encode() + data[:64]).hexdigest()[:12]
    ext = Path(urlparse(url).path).suffix.lower()
    if ext not in {".jpg",".jpeg",".png",".gif",".webp"}:
        ext = ".jpg"
    return f"{digest}{ext}"
def shrink_image(path: Path) -> Path:
    try:
        im = Image.open(path)
        if im.mode not in {"RGB", "L"}:
            im = im.convert("RGB")
        if max(im.size) > 1400:
            im.thumbnail((1400, 1400), Image.Resampling.LANCZOS)
        dest = path if path.suffix.lower() in {".jpg",".jpeg"} else path.with_suffix(".jpg")
        im.save(dest, "JPEG", quality=82, optimize=True)
        if dest != path and path.exists():
            path.unlink(missing_ok=True)
        return dest
    except Exception:
        return path
def download_images(blocks: list[dict[str, Any]], dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    session = requests.Session(); session.headers["User-Agent"] = UA
    count = 0
    def save_one(url: str, extras: list[str]) -> str | None:
        nonlocal count
        if count >= MAX_IMAGES:
            return None
        candidates = [url] + [u for u in extras if u != url]
        candidates.sort(key=lambda u: ("/thumbnails/" in u, len(u)))
        for cand in candidates:
            if cand.startswith("data:"):
                continue
            try:
                r = session.get(cand, timeout=TIMEOUT, stream=True)
                if r.status_code != 200 or "html" in (r.headers.get("Content-Type") or "").lower():
                    continue
                data = r.content
                if not data or len(data) > MAX_IMAGE_BYTES or len(data) < 400:
                    continue
                local = dest / hashed_name(cand, data)
                local.write_bytes(data)
                local = shrink_image(local)
                count += 1
                return str(local)
            except requests.RequestException:
                continue
        return None
    for b in blocks:
        figs = [b] if b.get("type") == "figure" else (b.get("images") or [])
        for fig in figs:
            if fig.get("src"):
                path = save_one(fig["src"], fig.get("altsrc") or [])
                if path:
                    fig["local"] = path
def file_to_data_uri(path: str) -> str:
    pth = Path(path)
    return f"data:{mimetypes.guess_type(pth.name)[0] or 'image/jpeg'};base64,{base64.b64encode(pth.read_bytes()).decode('ascii')}"
def bundle_finale(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out, i = [], 0
    while i < len(blocks):
        b = blocks[i]
        text = b.get("text") or ""
        is_done = DONE_RE.search(text) or (b.get("type") == "figure" and DONE_RE.search(b.get("caption") or b.get("alt") or ""))
        if b["type"] in {"para", "figure"} and is_done:
            imgs, text_out = [], text
            if b["type"] == "figure":
                imgs.append(b); text_out = b.get("caption") or b.get("alt") or text
            j = i + 1
            while j < len(blocks) and blocks[j]["type"] == "figure":
                imgs.append(blocks[j]); j += 1
            out.append({"type": "step", "label": "Finished", "text": text_out, "images": imgs})
            i = j; continue
        out.append(b); i += 1
    if out and any(x.get("type") == "step" for x in out):
        trail = []
        while out and out[-1]["type"] == "figure":
            trail.append(out.pop())
        trail.reverse()
        if trail:
            last = next((x for x in reversed(out) if x.get("type") == "step"), None)
            if last and (last.get("label") or "").lower() == "finished":
                last.setdefault("images", []).extend(trail)
            elif last:
                out.append({"type": "step", "label": "Finished", "text": "Finished model", "images": trail})
            else:
                out.extend(trail)
    return out
def detect_how_to(blocks: list[dict[str, Any]]) -> bool:
    steps = sum(1 for b in blocks if b.get("type") == "step")
    figs = sum(1 for b in blocks if b.get("type") == "figure")
    step_figs = sum(len(b.get("images") or []) for b in blocks if b.get("type") == "step")
    return steps >= 3 or (figs + step_figs) >= 5
def render_html(*, title: str, url: str, site: str, intro: list[str], blocks: list[dict[str, Any]], comments: list[dict[str, str]] | None, page_size: str, css: str, columns: int) -> str:
    how_to = detect_how_to(blocks)
    cols = columns if columns else (2 if how_to else 1)
    def esc(s: str) -> str:
        return html.escape(s or "")
    def img_tag(fig: dict[str, Any]) -> str:
        local, src = fig.get("local"), fig.get("src") or ""
        alt = esc(fig.get("alt") or fig.get("caption") or "")
        if local and Path(local).exists():
            src = file_to_data_uri(local)
        return f'<div class="photo"><img src="{src}" alt="{alt}"></div>' if src else ""
    parts = ["<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>", f"<title>{esc(title)}</title>", f"<style>{css.replace('size: letter;', f'size: {page_size};')}</style></head><body>", "<header class='masthead'>", f"<h1>{esc(title)}</h1>", "<div class='meta'>", f"<div>Source - <a href='{esc(url)}'>{esc(url)}</a></div>"]
    extra = ([esc(site)] if site else []) + [date.today().isoformat()]
    parts += [f"<div>{' \u00b7 '.join(extra)}</div>", "</div></header>"]
    if intro:
        parts.append("<section class='intro'>")
        parts += [f"<p>{esc(p)}</p>" for p in intro]
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
                        parts.append(f"<p class='caption'>{esc(b['text'])}</p>")
                else:
                    parts.append("<div class='img-row'>")
                    parts += [img_tag(fig) for fig in imgs[:3]]
                    parts.append("</div>")
                    if b.get("text"):
                        parts.append(f"<p class='caption'>{esc(b['text'])}</p>")
                parts.append("</article>")
            elif b["type"] == "figure":
                parts.append("<article class='card'>")
                parts.append(img_tag(b))
                cap = b.get("caption") or b.get("alt") or ""
                if cap:
                    parts.append(f"<p class='caption'>{esc(cap)}</p>")
                parts.append("</article>")
            elif b["type"] == "heading":
                parts.append(f"<article class='card'><p class='caption'><strong>{esc(b['text'])}</strong></p></article>")
            elif b["type"] == "para":
                parts.append(f"<article class='card'><p class='caption'>{esc(b['text'])}</p></article>")
        parts.append("</section>")
    else:
        parts.append("<section class='prose'>")
        for b in blocks:
            if b["type"] == "heading":
                parts.append(f"<h2>{esc(b['text'])}</h2>")
            elif b["type"] == "para":
                parts.append(f"<p>{esc(b['text'])}</p>")
            elif b["type"] == "figure":
                parts.append("<figure>"); parts.append(img_tag(b))
                cap = b.get("caption") or b.get("alt") or ""
                if cap:
                    parts.append(f"<figcaption>{esc(cap)}</figcaption>")
                parts.append("</figure>")
            elif b["type"] == "step":
                parts.append(f"<h2>{esc(b.get('label') or 'Step')}</h2>")
                parts.append(f"<p>{esc(b.get('text') or '')}</p>")
                for fig in b.get("images") or []:
                    parts.append("<figure>"); parts.append(img_tag(fig)); parts.append("</figure>")
        parts.append("</section>")
    if comments:
        parts.append("<section class='comments'><h2>Comments</h2>")
        for c in comments:
            parts.append("<div class='comment'>")
            if c.get("author"):
                parts.append(f"<div class='who'>{esc(c['author'])}</div>")
            parts.append(f"<div>{esc(c.get('text') or '')}</div></div>")
        parts.append("</section>")
    parts.append("<p class='footer-note'>Printer-friendly extract. Layout generated locally; images and wording remain copyright of the source site.</p></body></html>")
    return "\n".join(parts)
def chrome_print(html_path: Path, pdf_path: Path) -> None:
    chrome = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    if not chrome:
        raise SystemExit("google-chrome / chromium not found")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage", "--allow-file-access-from-files", "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}", html_path.as_uri()]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    if proc.returncode != 0 or not pdf_path.exists() or pdf_path.stat().st_size < 200:
        raise SystemExit(f"Chrome print failed (code {proc.returncode}): {proc.stderr[-800:]}")
def weak_extraction(blocks, title, site) -> bool:
    figs = sum(1 for b in blocks if b["type"] == "figure")
    step_imgs = sum(len(b.get("images") or []) for b in blocks if b["type"] == "step")
    paras = sum(1 for b in blocks if b["type"] in {"para", "step"})
    return (paras < 2 and (figs + step_imgs) < 2) or (bool(title and site and title.lower() == site.lower()))
def load_from_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if "blocks" not in data:
        raise SystemExit("--from-json file missing 'blocks'")
    return data
def main() -> int:
    p = argparse.ArgumentParser(description="Convert a webpage into a compact printable PDF")
    p.add_argument("--url"); p.add_argument("--from-json"); p.add_argument("--out", required=True)
    p.add_argument("--html-out"); p.add_argument("--comments", action="store_true")
    p.add_argument("--page-size", default="letter", choices=["letter", "a4"])
    p.add_argument("--columns", type=int, default=0); p.add_argument("--keep-work", action="store_true")
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
            strip_chrome(soup)
            title = page_title(soup, final_url)
            site = site_name(soup, final_url)
            blocks = extract_blocks(pick_container(soup), final_url)
            blocks = pair_short_labels(blocks)
            intro_list, blocks = intro_from_blocks(blocks)
            if not intro_list:
                ogd = soup.find("meta", attrs={"property": "og:description"}) or soup.find("meta", attrs={"name": "description"})
                if ogd and ogd.get("content"):
                    intro_list = [ogd["content"].strip()]
            url = final_url
            blocks, reader_comments = split_reader_comments(blocks)
            comments = reader_comments + (extract_comments(BeautifulSoup(html_text, "lxml")) if args.comments else [])
        blocks = pair_short_labels(blocks)
        blocks = bundle_finale(blocks)
        if not args.comments:
            comments = []
        download_images(blocks, work / "img")
        html_doc = render_html(title=title, url=url, site=site, intro=intro_list, blocks=blocks, comments=comments, page_size=args.page_size, css=css, columns=args.columns)
        html_path = Path(args.html_out) if args.html_out else work / "print.html"
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(html_doc, encoding="utf-8")
        out = Path(args.out)
        chrome_print(html_path, out)
        print(f"Wrote {out} ({out.stat().st_size} bytes)")
        print(f"title: {title}\nurl: {url}\ncomments: {len(comments)}\nhtml: {html_path}")
        if weak_extraction(blocks, title, site):
            print("WARN: weak extraction — consider --from-json via browser-extract.js")
            return 2
        return 0
    finally:
        if not args.keep_work:
            shutil.rmtree(work, ignore_errors=True)
if __name__ == "__main__":
    sys.exit(main())
