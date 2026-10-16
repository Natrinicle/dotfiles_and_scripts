---
name: shell-history-integrity
description: "Assess whether Linux shell history was suppressed, cleared, or timestamps were never enabled. Use when an empty or truncated .bash_history appears on an otherwise active account; chain into incident reports."
type: knowledge
lifecycle: active
---

# Shell History Integrity

Treat missing or manipulated command history as an indicator, not proof of guilt.

## Indicators of suppression or wiping

- Empty or abnormally short `.bash_history` (or `.zsh_history`) on an account that shows other activity.
- `HISTCONTROL=ignorespace` (or `ignoreboth`) — leading-space commands are not recorded.
- `HISTFILE=/dev/null`, `HISTSIZE=0`, `HISTFILESIZE=0`, or `unset HISTFILE` in profiles or environment.
- `history -c` / `history -w` patterns, or truncated file timestamps that do not match last login.
- Absence of `HISTTIMEFORMAT` — no per-command timestamps even if history exists.

## Analysis Steps

1. Check history file size and mtime for each interactive account (including root).
2. Inspect shell rc files and `/proc/<pid>/environ` (if live) for suppression variables.
3. Note whether `HISTTIMEFORMAT` was set.
4. Correlate with `wtmp`, auth logs, or auditd for activity that should have produced history.

## Output Format (for chaining)

```
HISTORY_INTEGRITY
account: "..."
history_file: present|empty|missing|truncated
suppression_vars: [ "HISTFILE=/dev/null", ... ]
timestamps_enabled: true|false
conclusion: suppressed|normal|inconclusive
notes: short bullets
```

## Companions

- `powershell-history-integrity` (thin)

When updating, keep the suppression-variable list and conclusion field stable.
