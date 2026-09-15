# Extraction and layout

Loaded when the converter produced a weak PDF or the user wants a layout change.

## Extraction order

1. `requests` GET with a desktop UA, 25s timeout, size cap 8 MiB.
2. `lxml` / `bs4` parse.
3. Drop `script`, `style`, `noscript`, `iframe`, `form`, `button`, `input`, `nav`, `footer`, `aside`, `[role=navigation]`, `[role=banner]`, `[role=complementary]`.
4. Drop nodes whose `id`/`class` match (case-insensitive):

   `nav`, `menu`, `sidebar`, `advert`, `adsbygoogle`, `cookie`, `social`, `share`, `related`, `popular`, `recommend`, `subscribe`, `newsletter`, `popup`, `modal`, `breadcrumb`, `header-wrap`, `sitenav`, `translate`.

5. Score remaining containers (`article`, `main`, `#content`, `.post`, `.entry`, `#main`, body descendants) by:

   `text_chars + 400*images + 80*paragraphs - 3*link_chars`

   Reject nodes with link-density above 0.55 unless they also have several large images.
6. Walk the winning container in document order into blocks — `heading`, `para`, `figure` (img + nearest caption / preceding step sentence), `list`.
7. Comments are a separate pass over `#comments`, `.comments`, `.comment-list`, `#disqus_thread` clones that already rendered as HTML. Default discarded.

## Image keep / drop

Keep when any of:

- Intrinsic or attribute width ≥ 80px and the URL is not a sprite/icon path
- `alt` looks like a step (`step 3`, `fold`, `diagram`)
- Path sits under the same directory as other large content images

Drop when:

- `1x1`, `pixel`, `cleardot`, `poweredby`, `sprite`, `icon`, `logo` (unless it is the only branding and we already have a title)
- Host looks like an ad network
- File is a sidebar 100px "most popular" thumb while larger article images exist
- Duplicate of an already-kept URL (ignore query-cache-busters)

Upgrade `/thumbnails/foo.jpg` → `/foo.jpg` when the larger sibling returns 200 and is an image.

Cap downloaded images at 40 per page. Re-encode to JPEG/PNG under ~1600px on the long side so print CSS can size them.

## Print CSS knobs

Edit `assets/print.css` (copied into the generated HTML). Useful levers:

| Goal | Change |
|------|--------|
| Fewer pages | raise grid to 3 columns, drop `img` max-height to ~140px, shrink `.intro` |
| More readable | 1 column, `img` max-height 240px, body 11pt |
| Photo-heavy how-to | 2 columns, `break-inside: avoid` on `.card` |
| Comments included | `.comments { columns: 2; font-size: 8.5pt; }` |

Page size is set with `@page { size: letter; }` or `a4`. Chrome `--print-to-pdf` honors that plus `--no-pdf-header-footer` so we own the footer.

## Weak-extraction fallback

Use `references/browser-extract.js` in a live browser tool when:

- requests is blocked / returns a cookie wall
- the article is client-rendered
- the script kept fewer than 2 content images on a page that visibly has a step gallery

Save the returned JSON and run:

```bash
python3 .../webpage_to_print.py --from-json extract.json --out out.pdf
```

The JSON shape is documented at the top of `scripts/webpage_to_print.py`.
