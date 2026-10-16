---
name: log-clearing-indicators
description: "Detect signs that logs were cleared or truncated: empty or suddenly-short auth logs, missing journal, cleared Windows Security log, or gaps that align with other anti-forensic activity. Use with shell-history and timestomp skills."
type: knowledge
lifecycle: active
---

# Log Clearing Indicators

Treat log gaps as an indicator, not proof of guilt. Correlate with other skills.

## Indicators

- Linux: `/var/log/auth.log` or `secure` that starts mid-incident, is zero-length, or is missing while journald shows activity.
- systemd journal: missing or truncated for the window of interest; `journalctl --list-boots` gaps.
- Windows: Security log cleared (Event ID 1102), System log cleared, or sudden size drop.
- Alignment with `shell-history-integrity` suppression or `timestomp-detection` on the same host and window.

## Steps

1. Check log file sizes, mtimes, and first/last entries for the relevant window.
2. Cross-check journald or Windows event channels.
3. Note whether the gap coincides with history suppression or timestamp anomalies.

## Output Format (for chaining)

```
LOG_CLEAR_FLAGS
items:
  - log: auth.log|journal|Security|System
    status: truncated|missing|cleared|gap
    window: "..."
    correlates_with: history|timestomp|none
conclusion: indicators_present|none_observed
notes: short bullets
```

## Companions

- `server-log-clearing-indicators`

When updating, keep the status and correlates_with fields stable.
