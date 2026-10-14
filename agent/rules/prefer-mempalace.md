---
paths:
  - "**"
---

# Prefer MemPalace over local files

Durable facts, findings, as-builts, preferences, interface notes, and
session continuity live in **MemPalace** (knowledge graph + drawers).
Agents on one host share one HTTP hub. Search and write the palace rather
than a private `{MEMORY_ROOT}/*.md` copy.

## Lookup

On a named person, project, decision, preference, or interface:
`mempalace_kg_query` then `mempalace_search` **before** reading a local
memory file or scraping the web. Current KG, then newest `filed_at`.

## Write

Stage a directory, `kg_add` / `kg_supersede` immediately, then one mine
through the hub or `mempalace mine --daemon`. Do not open a second
in-process palace (stdio fallback, extra container MCP, or `--direct`
beside the hub).

## What stays on disk

The harness loads **files**: `SKILL.md`, rules, hooks, systemd units,
client config. Keep those on disk. After you change a fact they encode,
file or supersede it in the palace so other agents see it.

Local memory files are staging and harness bootstrap. When they disagree
with the palace, the palace wins. Timeline: `mempalace-timeline-supersede`.
Concurrent hub: a multi-process backend (Qdrant or pgvector) plus
`MEMPALACE_MCP_ALLOW_PEER_WRITER` and the write daemon. Replicable setup:
pack `examples/mempalace-multi-rw/` (not installed by `install.sh --agent`).

## Pack scope

This rule ships in the general `dotfiles_and_scripts` agent pack. Do not
copy it into domain-only toolkits.
