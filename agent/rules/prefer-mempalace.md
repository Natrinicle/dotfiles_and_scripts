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

Lazy-load triggers (rule `lazy-load-data`) are **palace-only** for filed
as-builts. Do not also `Read` a `{MEMORY_ROOT}` copy of the same note.
If search is empty: widen once, then use a disk fallback only when that
rule still lists a file that exists. Empty palace ≠ invent.

## Write

Stage a directory, `kg_add` / `kg_supersede` immediately, then
`mempalace mine DIR --daemon` (agents add `--background`, record the
job id, search-verify when it succeeds). Pass `--daemon` so
`write_routing=prefer` cannot fall back to `--direct`.

Do not MCP `mempalace_mine` (it takes the palace lock and returns
`LockHeldByOtherProcess` while the daemon is writing). Do not use
`add_drawer` as a directory mine (interface cards only —
`mempalace-file-interfaces`). `--direct` only if the daemon is down
**and** the user named that fallback. Do not open a second in-process
palace (stdio fallback, extra container MCP).

Recovered command sequences (AT, GATT, UART, HTTP, MCP tool order, host
radios that reach a device): file the **same turn** per
`mempalace-file-interfaces`, before the user-facing answer. A chat recap
is not filing. Palace `add_drawer` is the commit. It is not a git commit.

Research claims you are about to vault: run **claim-source-check** first
(claim + source only). File `supported` pages. Rewrite the rest.

Parent compaction: file necessary pieces first (rule
`mempalace-compact-filing`) so later lookup has full drawers. The compact
summary is not filing.

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
