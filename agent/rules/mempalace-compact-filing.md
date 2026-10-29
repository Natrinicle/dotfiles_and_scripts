---
paths:
  - "**"
---

# File necessary pieces to MemPalace before compaction

Parent compaction replaces live context with a summary. Successive
summaries lose detail. File pieces that later lookup still needs into
**MemPalace** so the next session reads full drawers, not the compact
summary.

## When

File before the parent window is compacted:

- When compact is imminent (low remaining parent context, PreCompact)
- When this turn is a continuation after compact
- Recovered APIs / CLIs / devices still follow `mempalace-file-interfaces`
  the same turn they are found

Do not wait for the user to say "save this." Palace `add_drawer` /
`kg_add` / `kg_supersede` is the commit. It is not a git commit.

## What to file

Decisions, constraints, dirty paths, unique phrases, SHAs, command
sequences, KG facts, pack versions, and lookup keys a later agent would
otherwise rediscover. Verbatim cards. Keep older drawers;
`kg_supersede` current truth.

## What is not filing

- The compact summary
- A chat recap of those pieces
- Mining whole `compaction/segment_*.md` transcripts
- The remember-plugin markdown handoff

Harness session dirs may already keep full turn text on disk (Grok:
session `compaction/`). Palace holds **lookup keys**; open the segment
when you need the raw turn.

## Lookup later

`mempalace_kg_query` then `mempalace_search`. Do not treat the
successive compact summary as the source of truth.

Procedure: skill `mempalace` (compaction-time filing). Cost of the
compact pass: skill `expected-value` (`C_compact_parent`). Write
protocol: `prefer-mempalace`.
