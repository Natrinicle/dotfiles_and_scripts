---
name: mempalace
description: >
  Mine projects and conversations into a local searchable memory palace.
  Also use when asked to save findings to MemPalace. Also use when recovering
  GATT UUIDs, AT commands, UART/HTTP frames, MCP tool order, or other protocol
  sequences — file those the same turn without waiting to be asked.
  Also use before parent compaction to file necessary pieces so later
  lookup has full drawers.
---

# MemPalace

Install/configure via CLI when needed; mine trees or conversation exports;
organize with wings/rooms. Prefer CLI/MCP tools from the install. Pair with
`mempalace-recall` for search-before-answer on past work. File recovered
command sequences the **same turn** per rule `mempalace-file-interfaces`.
Durable facts prefer the palace over local memory files (`prefer-mempalace`).
Harness skills/rules stay on disk. Before parent compact, file necessary
pieces per rule `mempalace-compact-filing`. The compact summary is not
filing. Compact **cost** is skill `expected-value` (`C_compact_parent`).

**`mine` takes a directory, not a file.** Always `mempalace mine DIR --daemon`.
Trust `Files processed ≥ 1` and `Drawers filed ≥ 1`, then search-verify the
Source filename. Exit code 0 alone is not enough.

## Concurrent agents

All clients share one HTTP hub on a multi-process backend (Qdrant or
pgvector). Do not open a second in-process palace. `kg_add` is lock-free.
Directory mines: `mempalace mine DIR --daemon` (agents add `--background`).
Do not MCP `mempalace_mine` (palace lock). Do not use `add_drawer` as a
mine. `--direct` only if the daemon is down and the user named that
fallback. Hub + daemon + Qdrant setup: pack `examples/mempalace-multi-rw/`.

## Single-file mine recipe

Stage under a path the palace **hub** can read. If the hub systemd unit uses
`PrivateTmp=true`, host `/tmp` and `mktemp -d` fail with `source not found`.
Always pass `--mode projects` (or `convos` / `extract`); omitting mode can
fail as `invalid mode 'None'`.

```bash
STAGE="${HOME}/.mempalace/staging/$(date +%F)-topic"
mkdir -p "$STAGE"
cp /absolute/path/to/note.md "$STAGE/"
mempalace mine "$STAGE" --mode projects --wing <wing> --agent {user} --daemon
# Agents: add --background, record the job id, search-verify when succeeded.
# mempalace daemon wait <job_id>
mempalace search "unique phrase from note" --wing <wing>
```

Always pass `--wing` for known projects (`personal`, `technical`, `{project}`,
…). Without it, wing defaults to the directory basename.

Optional: `--dry-run` before a real mine.

## After mining

1. Confirm summary: files processed, drawers filed
2. `mempalace search "…" --wing <wing>` — top hit Source is the file you filed
3. `mempalace status` if you need wing counts

## Compaction-time filing

Before parent compact or on a compact continuation, file pieces later
lookup still needs. Do not wait to be asked.

File decisions, constraints, dirty paths, unique phrases, SHAs, command
sequences, and KG facts as verbatim cards. Keep older drawers;
`kg_supersede` current truth.

1. Lookup: `kg_query` then `search`. Skip only when current KG plus the
   newest drawer already holds those facts.
2. Cards: `add_drawer` (wing and room set) + `kg_add` / `kg_supersede`.
3. Staged notes: `mempalace mine DIR --daemon` (agents add `--background`).
4. Search-verify the unique phrase. 0 drawers means it is not filed.

Do not `add_drawer` the whole transcript. Session `compaction/segment_*.md`
stays on disk for grep. A PostCompact hook mines `compaction/INDEX.md` as
a pointer only (`{AGENT_HOME}/hooks/mempalace-postcompact-index.py`). Do
not mine `segment_*.md`. After compact: `kg_query` then `search`.

## Timeline — supersede current, keep history

Older memories stay searchable. A newer fact expires current truth via
`mempalace_kg_supersede` (`valid_to` on the old triple). Leave older drawers
in place.

When saving a replacement:

1. `mempalace_kg_query` (no `as_of`)
2. `mempalace_kg_supersede(subject, predicate, old_object, new_object, at=YYYY-MM-DD)` — object max 128 chars
3. Mine a dated card with `as_of:`, `status: current`, `SUPERSEDES:`

Hybrid search ranks similarity only. Conflicting drawers: current KG, then
newest `filed_at`. SOP: `{MEMORY_ROOT}/mempalace-recency-and-preferences.md`.

## Unhappy paths

- **0 drawers / skipped all** — file path passed, or content already filed
- **LockHeldByOtherProcess / MCP mine stalled** — use CLI `mempalace mine DIR --daemon`; do not `add_drawer` as a substitute
- **Index corrupt / HNSW / compaction** — `mempalace repair --mode from-sqlite --archive-existing --yes` first; re-mine drops MCP/diary-only drawers
- **Empty search** — say so; do not invent palace content
