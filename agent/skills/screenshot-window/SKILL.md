---
name: screenshot-window
description: Use when capturing one KDE/KWin window, plasmoid, or plasmawindowed preview without activating it, without notifications, or when spectacle -a grabbed the wrong window.
---

# Screenshot window

Capture **one** window by KWin UUID or unique caption. Do not activate it. Do not notify. Write under `/tmp/agent-screenshots/`.

**REQUIRED** parent: **screenshot** (dispatch). Browser pages: **screenshot-webpage**. Thread evidence: **thread-screenshots**.

## Command

PATH: `screenshot-window`. First run: `screenshot-window doctor` (compiles `kwin-screenshot2`, installs a NoDisplay `.desktop`, `kbuildsycoca6`).

```bash
screenshot-window list --all
screenshot-window capture --title "UNIQUE CAPTION"
screenshot-window capture --uuid '{...}'
screenshot-window cleanup
```

`list --all` includes skipTaskbar (plasmawindowed). Default `list` hides those. Ambiguous `--title` / `--class` prints matches and exits 2. Agent-terminal captions often contain the same words as the target — use a unique substring or the UUID.

Dest: `/tmp/agent-screenshots/<slug>-<UTC>.png` or `SCREENSHOT_WINDOW_DIR`. `cleanup` refuses paths outside `/tmp` unless `--force`.

## Capture rules

1. `list` (or `list --json --all`) and pick a **unique** match.
2. `capture` that UUID or title. Read the PNG. Confirm it is that window.
3. Do not activate, raise, move, or `keepAbove` the target.
4. Do not capture password managers, mail, or messengers unless the user named that window.
5. After the user is done looking, or when they ask: `screenshot-window cleanup` (or `--path` one file).

Helper is a compiled binary (`~/.local/lib/screenshot-window/kwin-screenshot2`) calling KWin `ScreenShot2.CaptureWindow`. Python cannot be the D-Bus caller on older Plasma (exe must match `.desktop` `Exec=`). Plasma 6.7 dropped that auth check; still install the desktop. Drain the D-Bus reply from libdbus's buffer — do not `poll()` the socket only (buffered reply looks like a hang).

## Common mistakes

| Excuse | Reality |
|--------|---------|
| `spectacle -a` is faster | It captures the focused window, usually the agent terminal |
| Activate, then capture | User stays in other windows; activate/move grabs the wrong text |
| grim / fullscreen | Other windows' pixels land in the PNG |
| `~/Pictures/Screenshots` | Use `/tmp/agent-screenshots/` so reboot clears leftovers |
| Delete the PNG immediately | The agent still needs to read it; cleanup when looking is done |

## Red flags

- `spectacle`, `--activewindow`, `-a`, grim without a window handle
- KWin scripts that `requestActivate` / `keepAbove` before a shot
- Writing PNGs under `$HOME`
- Capturing a grok/claude terminal because the caption also mentions the app under test
