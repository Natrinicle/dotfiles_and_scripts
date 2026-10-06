---
name: mempalace
description: >
  Mine projects and conversations into a local searchable memory palace.
  Also use when asked to save all findings to MemPalace, save relevant details
  to MemPalace, save findings into MemPalace, update MemPalace with any
  relevant findings, or save all these findings to MemPalace.
---

# MemPalace

Install/configure via CLI when needed; mine trees or conversation exports;
organize with wings/rooms. Prefer CLI/MCP tools from the install. Pair with
`mempalace-recall` for search-before-answer on past work.

**`mine` takes a directory, not a file.** Trust `Files processed ≥ 1` and
`Drawers filed ≥ 1`, then search-verify the Source filename. Exit code 0 alone
is not enough.

## Single-file mine recipe

Stage under a path the palace **hub** can read. If the hub systemd unit uses
`PrivateTmp=true`, host `/tmp` and `mktemp -d` fail with `source not found`.
Always pass `--mode projects` (or `convos` / `extract`); omitting mode can
fail as `invalid mode 'None'`.

```bash
STAGE="${HOME}/.mempalace/staging/$(date +%F)-topic"
mkdir -p "$STAGE"
cp /absolute/path/to/note.md "$STAGE/"
mempalace mine "$STAGE" --mode projects --wing <wing> --agent {user}
mempalace search "unique phrase from note" --wing <wing>
```

Always pass `--wing` for known projects (`personal`, `technical`, `{project}`,
…). Without it, wing defaults to the directory basename.

Optional: `--dry-run` before a real mine.

## After mining

1. Confirm summary: files processed, drawers filed
2. `mempalace search "…" --wing <wing>` — top hit Source is the file you filed
3. `mempalace status` if you need wing counts

## Unhappy paths

- **0 drawers / skipped all** — file path passed, or content already filed
- **Index corrupt / HNSW / compaction** — `mempalace repair --mode from-sqlite --archive-existing --yes` first; re-mine drops MCP/diary-only drawers
- **Empty search** — say so; do not invent palace content
