---
name: server-execution-evidence
description: "Server companion to execution-evidence. Reuse the presence-vs-execution distinction, then add auditd execve, journalctl, and process accounting for Linux and Windows Server hosts."
type: knowledge
lifecycle: active
---

# Server Execution Evidence

Thin companion to `execution-evidence`.

## Core reuse

Apply `execution-evidence` for Windows artifacts and the reliability rating.

## Server additions

- Linux: `auditd` `EXECVE` records, `journalctl` unit starts, `/proc/<pid>/exe` (even if deleted), bash history, cron.
- Windows Server: Prefetch usually disabled; rely on Sysmon 1, 4688, or audit policy if enabled.
- Container: image layer history vs runtime process start.

## Output

Same `EXECUTION_EVIDENCE` block; add `source: prefetch|auditd|journal|sysmon|4688` and `server_context: linux|windows-server|container`.

## Upstream note

Reliability scale and presence-vs-execution distinction must stay compatible.
