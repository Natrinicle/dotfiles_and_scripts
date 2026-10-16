---
name: server-persistence-indicators
description: "Server companion to persistence-indicators. Apply the core checklist, then add Linux systemd/cron and Windows Server service/task specifics for hosts that rarely have interactive Explorer activity."
type: knowledge
lifecycle: active
---

# Server Persistence Indicators

Thin companion to `persistence-indicators`.

## Core reuse

Follow the core skill for locations and the `PERSISTENCE_FLAGS` block.

## Server additions

- Linux: focus on system units, timers, and root cron; note user cron only if interactive accounts exist.
- Windows Server: scheduled tasks and services are primary; Run keys are less common.
- Container: image entrypoint or added cron inside a container vs host.

## Output

Same `PERSISTENCE_FLAGS` block; add `context: linux-server|windows-server|container`.

## Upstream note

Type and baseline_match fields must stay compatible.
