---
name: persistence-indicators
description: "Detect unexpected persistence mechanisms: cron, systemd timers, Windows Run/Services, scheduled tasks, and startup items. Use when looking for residual access after an incident; chain with install-dating and execution-evidence."
type: knowledge
lifecycle: active
---

# Persistence Indicators

Look for mechanisms that survive reboot or logoff and were not part of the known baseline.

## Common locations

- Linux: `/etc/cron.*`, `/var/spool/cron`, `systemd` user/system units and timers, `~/.bashrc` / profile hooks, `@reboot` entries.
- Windows: `HKLM\Software\Microsoft\Windows\CurrentVersion\Run` (and RunOnce, RunServices), scheduled tasks, services with non-standard ImagePath, startup folders.

## Steps

1. Enumerate the locations above.
2. Compare against a known-good baseline or recent change window when available.
3. Note creation/modification times and the binary or script that would run.
4. Cross-check the binary with `execution-evidence` and the install time with `software-install-dating`.

## Output Format (for chaining)

```
PERSISTENCE_FLAGS
items:
  - type: cron|systemd|run-key|scheduled-task|service|startup
    location: "..."
    target: "..."
    mtime: "..."
    baseline_match: true|false|unknown
conclusion: unexpected|baseline|none_observed
notes: short bullets
```

## Companions

- `server-persistence-indicators`

When updating, keep the type and baseline_match fields stable for callers.
