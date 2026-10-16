---
name: credential-access-indicators
description: "Detect signs of credential access: new SSH keys, sudoers changes, dumped credential files, LSASS-related access patterns, and unexpected password-auth enablement. Use during incident response; chain with account-audit and shell-history skills."
type: knowledge
lifecycle: active
---

# Credential Access Indicators

Look for evidence that credentials were read, dumped, or newly added.

## Indicators

- New or recently modified `authorized_keys`, SSH private keys in unusual locations, or `known_hosts` changes.
- `/etc/sudoers` or `sudoers.d` modifications outside change windows.
- Files named like credential dumps (`*.dmp`, `lsass.dmp`, `ntds.dit` copies, `.kirbi`).
- Windows: access to LSASS (Prefetch or 4688 for procdump/mimikatz-style tools), SAM/SECURITY hive copies.
- Linux: unexpected `passwd`/`shadow` reads in auditd when enabled.

## Steps

1. Enumerate the locations above and note mtimes.
2. Correlate with `server-account-audit` for new accounts and `shell-history-integrity` for suppression around the same window.
3. If execution evidence exists for known dumpers, record it.

## Output Format (for chaining)

```
CRED_ACCESS_FLAGS
items:
  - type: ssh-key|sudoers|dump-file|lsass-access|shadow-read
    path: "..."
    mtime: "..."
    notes: short
conclusion: indicators_present|none_observed
```

## Companions

- `server-credential-access-indicators`

When updating, keep the type list and conclusion field stable.
