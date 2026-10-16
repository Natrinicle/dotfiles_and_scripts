---
name: server-log-clearing-indicators
description: "Server companion to log-clearing-indicators. Apply the core gap and truncation checks, then add journald-first and Windows Server event-channel specifics."
type: knowledge
lifecycle: active
---

# Server Log Clearing Indicators

Thin companion to `log-clearing-indicators`.

## Core reuse

Follow the core skill and emit `LOG_CLEAR_FLAGS`.

## Server additions

- Linux: on modern systemd hosts, empty `auth.log` is normal if rsyslog is not forwarding; check the journal first.
- Windows Server: Event ID 1102 and channel size history; note if audit policy was never enabled.
- Correlate with the history and timestomp companions already in the toolkit.

## Output

Same block; add `primary_source: journald|syslog|eventlog`.

## Upstream note

Status and correlates_with fields must stay compatible.
