---
name: screenshot-webpage
description: Use when capturing a browser page or URL (not a desktop window). GitHub/Slack thread evidence stays on thread-screenshots.
---

# Screenshot webpage

Thin wrap. Load **browser-testing-with-devtools** (Chrome DevTools MCP) and take the page screenshot there.

**REQUIRED** parent: **screenshot**. Desktop windows: **screenshot-window**. GitHub/Slack thread evidence directories: **thread-screenshots**.

## Rules

- Capture the **page** (tab/element), not the browser window via KWin, unless the user asked for chrome and OS decorations.
- Prefer saving under `/tmp/agent-screenshots/` when the MCP lets you choose a path. If the MCP only writes a tool-owned dir, copy into `/tmp/agent-screenshots/` then delete the extra copy when cleanup runs.
- Do not attach to the user's daily browser profile for a shot that only needs localhost. Skill **browser-testing-with-devtools** owns profile isolation.
- Cleanup when the user asks or when the visual QA pass is done looking: `screenshot-window cleanup` also wipes `/tmp/agent-screenshots/`.
