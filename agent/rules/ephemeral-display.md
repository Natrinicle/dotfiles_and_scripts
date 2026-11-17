---
paths:
  - "**"
---

# Ephemeral display

When the agent needs a nested Plasma, plasmawindowed preview, QML window,
isolated Chromium, Docker webtop, a GUI the user will not operate, or any
other display that must not linger, load skill **ephemeral-display**.
PATH: `ephemeral-display`.

Prefer `ephemeral-display run …` so the lab stops in `finally`. `start`
without `stop` in the same turn is a leak. `gc` dead/stale labs on entry;
`stop --all` if a lab might still be up.

Window pixels: **screenshot-window**. Pages the user is not browsing:
`chrome-shot` / `chrome`, or **screenshot-webpage** on an `--isolated`
DevTools browser that you close. Host `plasmashell` stays up. Nested
kwin uses a private session bus; never `--replace` / `kquitapp plasmashell`.
