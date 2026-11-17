---
name: ephemeral-display
description: Use when an agent needs a nested Plasma, plasmawindowed preview, QML window, isolated Chromium, Docker webtop, or other display the user will not operate; leftover labs; screenshots of a preview the user is not using; a non-interactive browser that must not touch the daily profile.
---

# Ephemeral display

Start an **agent-only** display, do the work, tear it down in the same turn. The user's Plasma session stays up.

PATH: `ephemeral-display`. Prefer `run` (always stops). `start` without `stop` is a leak.

**REQUIRED SUB-SKILL:** **screenshot-window** for a KWin window / plasmawindowed / nested compositor window.
**REQUIRED SUB-SKILL:** **screenshot-webpage** when Chrome DevTools MCP is already the browser (still `gc` leftover labs).
**REQUIRED SUB-SKILL:** **browser-testing-with-devtools** for DOM/console on a page; spawn `--isolated` and close when done.

| Need | Kind |
|------|------|
| Plasmoid or wallpaper preview window | `plasmawindowed` |
| QML `Window` file | `qml` |
| Any GUI the user will not operate | `app` (`--exec 'binary args'`) |
| Real wallpaper plugin, tray, Desktop Settings, plasmashell restart | `nested-kwin` (private session bus; `--virtual` has no host window) |
| One URL still | `chrome-shot` (Chromium `--screenshot`, process exits) |
| Several shots / CDP on one isolated browser | `chrome` |
| Clean distro Plasma | `webtop` (image must already exist unless the user named `--pull`) |

```bash
ephemeral-display gc
ephemeral-display run plasmawindowed --applet org.kde.plasma.analogclock --capture --title analog
ephemeral-display run qml --file /path/to/preview.qml --capture --title preview
ephemeral-display run app --exec 'plasmawindowed org.kde.plasma.analogclock' --capture --title analog
ephemeral-display run nested-kwin --width 1920 --height 1080 --exec plasmashell --capture --title kwin
ephemeral-display run nested-kwin --virtual --exec plasmashell
ephemeral-display run chrome-shot --url 'https://example.com'
ephemeral-display run chrome --url 'https://example.com' --capture
ephemeral-display doctor
ephemeral-display stop --all
```

Window captures go through `screenshot-window` (no activate, `/tmp/agent-screenshots/`). `chrome-shot` / `chrome` / webtop HTTPS shots use isolated Chromium `--user-data-dir` under `/tmp/ephemeral-display/<id>/chrome`. Nested kwin gets a private `dbus-daemon` and `--no-global-shortcuts` so it cannot claim host `plasmashell` or steal keys. `--replace`, `--drm`, `--fullscreen`, and `kquitapp plasmashell` are refused.

## Teardown

`run` stops in `finally`. After `start`: `stop ID` in the same turn, including on failure. Skill entry also `gc` (dead labs and labs older than 30 minutes). `stop --all` at the end of the visual pass when any lab might still be up.

Stop kills the recorded process group and any pid whose cmdline contains `/tmp/ephemeral-display/<id>`. It never signals host `plasmashell` or `kwin_wayland`.

## Guardrails

- Host `plasmashell` stays running. Nested `plasmashell` is a child of the lab `kwin_wayland`.
- Isolated Chromium only. Daily browser profiles stay closed.
- `webtop` does not `docker pull` unless the user named pull (`--pull`).
- Do not bind-mount the host Plasma `appletsrc` into a lab.
- `kwin_wayland --replace` and `plasmashell --replace` are refused.

`ephemeral-display --help` and `self-test` are the flag list. Capture rules stay on **screenshot-window**.
