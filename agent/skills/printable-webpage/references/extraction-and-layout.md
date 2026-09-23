# Extraction and layout

Generic first-pass notes. Do not add site names here.

## Fetch

1. `requests` GET, desktop UA, ~25s, cap ~8 MiB.
2. If blocked (401/403/429), empty, or a JS shell (almost no `<p>`/`<img>`, several `<script>`s), Chrome `--headless --dump-dom --virtual-time-budget=20000`.
3. Still thin → `browser-extract.js` + `--from-json`.

## Strip

Drop `script style noscript iframe form button input nav footer aside` and roles `navigation banner complementary contentinfo search`.

Drop nodes whose id/class/role look like: nav, menu, sidebar, advert, cookie, social, share, related, popular, recommend, subscribe, newsletter, popup, modal, breadcrumb, comment.

Keep a large `article`/`main` wrapper even if a hashed class contains one of those tokens.

## Choose the article

Score candidates (`article`, `main`, `[role=main]`, `#content`, `.post`, `.entry-content`, large descendants):

`text_chars + 400*content_images + 80*paragraphs - 3*link_chars`

Penalize link-density > 0.55 unless there are several real images.

## Blocks

Walk the winner in document order: heading, para, figure. Text matching `step N` starts a step; following images attach to it.

Skip tracking pixels, sprites, and images under ~80px. Prefer the largest `srcset` URL. If a path contains `/thumbnails/`, try the sibling without that segment.

Cap downloads (~40). Re-encode long edge under ~1600px.

## Layout

How-to (several numbered steps or many figures, little prose) → 2-column cards, `break-inside: avoid`, photos in a clipped `.photo` well.

Prose → one column.

Comments → two-column small type, only with `--comments`.

Knobs in `assets/print.css`: column count, `.photo` max-height, body point size, `@page` size.
