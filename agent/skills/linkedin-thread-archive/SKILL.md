---
name: linkedin-thread-archive
description: Use when archiving LinkedIn messaging threads or DMs to a searchable PDF via Voyager in-page fetch.
---

# LinkedIn Thread Archive

Pull a LinkedIn messaging thread as real text from a logged-in headed Chrome tab, then write a searchable PDF. Cookie-jar / Brave `li_at` fetches go stale (200 then 401). In-page `fetch` with the page's cookies is the working path.

This is a **text archive**, not screenshots. For GitHub/Slack screenshots use `thread-screenshots`.

## Hard rules

- Never type, paste, or `keyboard_press` into the LinkedIn compose box
- `pause_capture` before compose-adjacent eval
- Never `set_viewport` / `resize_page` / kill the user's Chrome
- Never print cookies, csrf values, or signed media URLs
- Leave `==` in the conversation id **unencoded**. Encoding the id → HTTP 400

## Browser

Announce the browsing skill. Drive `chrome__use_browser`: `list_tabs` → switch to the thread (or `navigate` if the user is already signed in). If `chrome-devtools-http` `list_pages` fails on a missing Chrome binary, stay on `use_browser`.

## CSRF — the method that works

```javascript
const csrf = (document.cookie.split(';').map(s => s.trim()).find(s => s.startsWith('JSESSIONID=')) || '').slice('JSESSIONID='.length).replace(/"/g, '');
```

Prefix is `ajax:`. Send it as header `csrf-token` (no extra quotes).

**Broken:** a regex cookie parser inside `eval`. MCP JSON-encodes the payload; a character-class `^` (`/[^;]/`, `/^…/`) throws `SyntaxError: Unexpected token '^'`. Same class of failure for any regex character class in `eval` JS. Use `split` / `startsWith`.

## Voyager GET

`https://www.linkedin.com/voyager/api/messaging/conversations/{THREAD_ID}/events?count=20`

| Header | Value |
|--------|--------|
| `accept` | `application/vnd.linkedin.normalized+json+2.1` |
| `csrf-token` | JSESSIONID as above |
| `x-restli-protocol-version` | `2.0.0` |
| credentials | `include` |

Paginate `createdBefore` = oldest `createdAt` ms. Stop when `nNew === 0`.

Parse `included[]` items with `$type` Event, `urn:li:messagingMessage:`, or `eventContent`. Sender: `*from` → `*miniProfile` → `firstName` `lastName`. Body: `attributedBody.text`.

Run `references/inpage-fetch.js` as the `eval` payload. Store the full dump on `window.__liThread`. Return a compact `{n, pages, nNewer, newer, last5}` from eval — a full JSON dump truncates around 20KB.

A blob `a.download` often does **not** land in `~/Downloads` on the superpowers Chrome profile. Merge `newer` onto a prior dump, or pull `JSON.stringify(window.__liThread).slice(start, end)` in chunks.

## PDF

- Filename `{YYYY-mm-dd} - LinkedIn - {contact}.pdf` (archive date, user prefix)
- reportlab + DejaVu TTF so `pdftotext` is real text
- Color emoji: Pillow + Noto Color Emoji PNG + ASCII CLDR names (WinAnsi cannot round-trip U+1Fxxx)
- Embed local attachment files; drop signed LinkedIn CDN URLs
- Timestamps in `{timezone}` unless the user named another zone

## After

File the archive **path** in MemPalace (`kg_query` entity `LinkedIn Voyager`). Do not store message bodies or medical transcript text in the palace. If the contact has a pattern file, invoke `communication-pattern-analysis`.
