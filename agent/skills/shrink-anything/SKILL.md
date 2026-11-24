---
name: shrink-anything
description: >
  Use when deleting dead code, unused files, unused dependencies, or dead
  assets, or when cleaning up after AI-generated or legacy code. Triggers:
  shrink anything, dead code, unused files, unused deps, lighter bundle,
  what in this repo is unused. Skip readability refactors
  (code-simplification) and RAM/binary footprint cuts.
---

# Shrink Anything

Test-gated deletion of code, files, dependencies, and assets the project
does not use. A cut stays only if the project's own check still passes.
Byte-for-byte undo. Tests are never edited.

## Pick the picture

| Ask | Skill |
|-----|--------|
| Dead code, unused files, unused deps, dead assets | **this skill** (`shrink-anything` CLI) |
| Readability, nesting, names; same behavior | **code-simplification** |
| RSS / binary size / drop a heavy runtime after it works | host **footprint-trimmer** (not in this pack) |
| Bug hunt | **find-patch-loop** |
| Session-complete verify | **check-work** |

Do not grow those skills to cover test-gated dead-code deletion.

## Reach

Read-only clone: `${HOME}/repos/external/shrink-anything` (MIT, v0.1.0).

Install the CLI when it is missing:

```bash
cargo install --path "${HOME}/repos/external/shrink-anything" --locked
# or: cargo install shrink-anything
# or: npm i -g @el4cteo/shrink-anything
```

Same steps as MCP tools when the server is registered: `shrink_scan`,
`shrink_cut`, `shrink_task`, `shrink_verify`, `shrink_undo`,
`shrink_report`, `shrink_weigh`, `shrink_status`. Copy
`examples/shrink-anything-mcp/` only when the user named MCP. Installing
this skill does not register the server.

`--agent` takes `claude`, `codex`, or any command that reads a prompt on
stdin. Without it, hand `.shrink/TASK.md` to the current agent.

## Loop

1. **Find the check** that fails when the project is broken (`npm test`,
   `pytest`, `cargo test`, `go test ./...`). It must pass before the first
   cut. Prefer the full suite plus type-check or build when one exists
   (`shrink-anything cut -- "npm run build && npm test"`). A project with
   no tests gets a scan, not a trusted cut.
2. **Scan**: `shrink-anything scan` (add `--all` for every candidate and
   why). Changes nothing.
3. **Cut**: `shrink-anything cut -- <check>`. Safe candidates go in as a
   batch; a failing check bisects until the bad cut is put back. Repeat
   because a cut can orphan more code. Add `--size dist` (or a binary) to
   weigh a build before and after.
4. **Judgment**: read `.shrink/TASK.md`.
   - Duplicates: keep one copy, point the others at it.
   - Probably dead: nothing mentions it, but a framework, reflection, or
     public API might still reach it. Delete only when that path is absent.
5. **Verify** after each group of edits: `shrink-anything verify`.
6. **Report**: `shrink-anything report`. Lines, files, dependencies, and
   tokens before and after, plus undo (`shrink-anything undo`, or `--all`).

`go --agent <cmd> -- <check>` runs scan, cut, and agent tasks in one shot.

Library public names stay. The CLI guesses `--lib` vs `--app`; override
when the guess is wrong. `--aggressive` on a library needs a named ask.

## Don't

- Edit, delete, or skip a test to make the check pass. `verify` fails when
  fewer tests run than before the first cut.
- Rewrite for style. Smallest diff, same behavior, fewer lines.
- Trust a cut the check cannot see.
- Reimplement the cutter by hand when the CLI is installable.

## Source

Upstream MIT skill from EL4CTEO/shrink-anything snapshot `28ef88d`
(2026-11-23, v0.1.0). Pack notice: `agent/THIRD-PARTY.md`.
