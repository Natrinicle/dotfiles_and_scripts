# Lazy-Load Data — palace first

Keep always-on context small. Durable as-builts live in **MemPalace**.
This rule is the trigger: query the palace, or read one remaining disk
file. Do not dual-load palace drawers and a `{MEMORY_ROOT}` copy of the
same note.

**Memory root:** `{MEMORY_ROOT}` — typically `~/.claude/memory` or
`~/.grok/memory` (often the same directory via symlink).

## One source

When a trigger matches a filed as-built:

1. `mempalace_kg_query` on the named entity (no `as_of`).
2. `mempalace_search` with the listed query and wing.
3. Use the drawer. Stop. Do not also `Read` a markdown copy.

If search returns **nothing**:

1. Widen **once** (drop room, shorten the query, try the other wing).
2. Only if a path is listed as a disk fallback **and** that file still
   exists: read it.
3. If still empty: say the palace has nothing; do not invent.

Harness SOPs, generated catalogs, style profiles, and unfiled notes stay
on disk. Those rows are file-sourced; skip palace for them unless the
row also names a palace query.

Do not read an operator archive of already-filed notes unless the user
names it. Do not `mempalace sync` in a way that prunes those drawers.

## When to lazy-load

- API catalogs, repo maps, long runbooks
- Security findings catalogs
- Person/contact profiles and communication notes
- Tool-specific setup guides (browser automation, local observability stacks)
- Model routing tables and cost sheets

## Pattern

1. Keep a short **trigger** in a rule or MEMORY index (when to load +
   palace entity/search, or one disk path).
2. Filed as-builts: palace is the source.
3. Unfiled / harness: put the full content under `{MEMORY_ROOT}/` and
   read that file only when the trigger matches.

## Suggested categories (adapt names to your workspace)

| Trigger | Source |
|---------|--------|
| Working in a large monorepo | `{MEMORY_ROOT}/workspace-repos.md`, `platform-repo-structure.md` |
| Security review of any code | `{MEMORY_ROOT}/vulnerability-patterns.md` |
| Building or exposing a host / VM / cluster | rule `system-security`; `{MEMORY_ROOT}/vulnerability-patterns.md` |
| Looking up an API, CLI, device, MCP, library, or protocol | rules `prefer-mempalace` + `mempalace-file-interfaces`; search palace first, then file methods the same turn. A chat recap is not filing. Palace `add_drawer` is the commit. |
| Compaction-time session continuity | rules `prefer-mempalace` + `mempalace-compact-filing`; file necessary pieces to palace before compact; lookup drawers later; the compact summary is not filing |
| Durable facts vs local memory files | rule `prefer-mempalace`; palace KG / newest `filed_at` wins |
| Preference / fact replacements over time | rule `mempalace-timeline-supersede`; `{MEMORY_ROOT}/mempalace-recency-and-preferences.md` |
| Browser automation | palace first (`browser control Chromium CDP`); disk fallback only if still listed |
| LinkedIn DM / Voyager thread archive | palace `LinkedIn Voyager messaging events csrf JSESSIONID`; skill `linkedin-thread-archive` |
| Local tracing / OTEL demos | palace first; disk fallback only if still listed |
| Decision models / System One (Jev Nimble Kev) | palace `Jev Nimble Kev System One gemma4` |
| Model routing / cost audits | `{MEMORY_ROOT}/model-routing-table.md` |
| Packaging a toolkit | `toolkit-homes.md`; classify first; rule `toolkit-residual-identity` (host denylist, never pack real names) |
| Reverse Engineer Anything / `rea-agents` / REA MCP | `{MEMORY_ROOT}/reverse-engineer-anything-2026-10-16.md` |
| Opening a PR in the current employer's GitHub org | rule `employer-pr-findings-gate`; `{MEMORY_ROOT}/employer-pr-findings-gate.md` |
| Repo has a pre-commit config | rule `pre-commit-gate`; `{MEMORY_ROOT}/pre-commit-gate.md` |
| gitleaks / hadolint canaries or CI CLI install (any repo) | `{MEMORY_ROOT}/scanner-self-test-correctness.md`; palace `kg_query` `gitleaks` / `hadolint`; charset `A-Z2-7` not `A-Z0-9` |
| Contacts / messaging analysis | contacts profiles (store carefully; may contain PII) |
| Change comparisons / Meld-style diffs / YAML JSON dyff | skill `meld-style-diff` |
| KDE / CUPS custom backend persist | palace `cups-custom-backend lpadmin retry-job last-seen print-manager list vs Add`; skill `cups-custom-backend` |

Do not list secrets, tokens, or private hostnames in always-loaded files.
