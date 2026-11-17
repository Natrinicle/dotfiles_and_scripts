---
paths:
  - "**"
---

# Screenshot dispatch

When capturing the screen, load skill **screenshot** and the matching sub-skill.

- Desktop window / plasmoid / plasmawindowed → **screenshot-window** (`screenshot-window` on PATH).
- Browser page / URL → **screenshot-webpage**.
- GitHub/Slack thread evidence → **thread-screenshots**.

Window shots: capture by UUID or unique caption. Do not activate the target. Do not notify. Write `/tmp/agent-screenshots/`. Cleanup when asked or when looking is done.

Do not use `spectacle -a` / `--activewindow`, grim/fullscreen of the output, or `~/Pictures/Screenshots`.
