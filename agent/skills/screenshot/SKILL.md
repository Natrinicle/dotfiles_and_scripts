---
name: screenshot
description: Use when capturing a desktop window, plasmoid, plasmawindowed preview, or a webpage, or when Spectacle, grim, or fullscreen capture would steal focus, notify, or grab the wrong window.
---

# Screenshot

Dispatcher only. Load the sub-skill. Do not capture here.

**REQUIRED SUB-SKILL:** **screenshot-window** for a KDE/KWin window, plasmoid, or plasmawindowed preview.
**REQUIRED SUB-SKILL:** **screenshot-webpage** for a browser page or URL.

GitHub/Slack thread evidence stays **thread-screenshots**. OCR of already-captured images stays **screenshot-writing-style**.

| Target | Sub-skill |
|--------|-----------|
| Desktop window, plasmoid, plasmawindowed | **screenshot-window** |
| Browser page / URL | **screenshot-webpage** |
| GitHub PR / Slack thread evidence | **thread-screenshots** |

Window helper on PATH: `screenshot-window`. Default dest `/tmp/agent-screenshots/` (reboot clears). Cleanup when the user asks, or when the visual QA pass is done looking.

## Do not

- `spectacle -a` / `--activewindow` / activate-then-capture
- Raise, `keepAbove`, or move the target so it is focused
- Full-screen / grim of the output (other windows' text lands in the PNG)
- Write under `~/Pictures/Screenshots` or elsewhere in `$HOME`
