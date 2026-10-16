---
name: server-credential-access-indicators
description: "Server companion to credential-access-indicators. Apply the core checks, then add Linux auditd/shadow and Windows Server LSASS/SAM specifics for non-interactive hosts."
type: knowledge
lifecycle: active
---

# Server Credential Access Indicators

Thin companion to `credential-access-indicators`.

## Core reuse

Follow the core skill and emit `CRED_ACCESS_FLAGS`.

## Server additions

- Linux: auditd watches on `/etc/shadow`, `/etc/passwd`, and SSH directories; note if auditd was not enabled.
- Windows Server: 4688 or Sysmon for LSASS access; SAM/SECURITY hive copies under temp or unusual paths.
- Absence of audit is itself a note, not proof.

## Output

Same block; add `audit_source: auditd|sysmon|4688|none`.

## Upstream note

Type list and conclusion must stay compatible.
