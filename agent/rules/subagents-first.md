---
paths:
  - "**"
---

# Subagents first

Spawn a child when the work is large enough that parent-do would cost more
than brief + re-ingest. The goal is **fewer parent tokens**, so a single
command whose output the parent must read anyway stays on the parent.

The user does **not** have to say “use subagents”.

Hook `prefer-spawn-search` **denies** forest and multi-location search
(`$HOME`, `/`, `~/repos`, missing-path workspace hunt, two+ directory
operands). A single `rg` / `grep` / `find` / `list_dir` of **one** tree
(including a git repo root) stays on the parent.

## Shape (do not collapse)

| Work | Run |
|------|-----|
| One command (`rg`, `grep`, `list_dir` of one tree) | Parent |
| Existing helper script | Parent (`prefer-helper-scripts`) |
| More than one command | Prefer a helper script; spawn only if the work is still large |
| One large child-capable unit | `spawn_subagent` |
| Several units that do not consume each other's output, or a gate / named output between steps | skill **agent-graphs** (workflow `agent-graph`). Inner retry is **loop-until-green**. |
| Bug hunt | **find-patch-loop** |
| Session-complete verify | **check-work** |

Do not grow this rule into graph topology. Do not dump several trees into
the parent “so the graph has context”.

## Spawn for

- Software install that includes config and service files
- Search across multiple locations (`$HOME`, `~/repos`, several trees)
- Decompile, protocol recovery, JADX/Ghidra/REA, unpack
- Architecture mapping, large-file extract
- Multi-file implementation, packing, README, tests, lint, palace filing
- Parallel independent slices (one child per slice)

## Parent keeps

- Single commands: `rg`, `grep`, `find` of one tree, `list_dir`, `git status`
- Calling an existing helper; writing one when the sequence is more than a
  single command (`prefer-helper-scripts`)
- Asking the user; landing approvals (commit / push / server)
- Synthesizing child reports into the user-facing answer
- Verification the user named, or a second look at child claims
  (self-test, residual-identity, palace search-verify, pre-commit)

## Spawn how

1. Put every path, constraint, and skill name in the child prompt. Children
   do not see this conversation.
2. Omit `model` so `[subagents.models]` pins apply. Do not load skill
   `model-router` or the routing table before spawn.
3. File-search / extract → native `explore` / `code-explorer` when the
   harness offers those types. **Grok Build does not:** `spawn_subagent`
   only lists plugin types. Omit `subagent_type` (cloud general-purpose) for
   multi-location unknown-path search. Do not use `feature-dev:code-explorer`
   with `ollama-gemma4` (16K window vs ~24K plugin inject).
4. Implementation, decompile, protocol judgment → `general-purpose` (cloud;
   do not pin to 8B local).
5. Several independent slices → spawn in parallel.

Every spawn scores **context-window** EV (skill `expected-value`): parent
tokens saved (`C_parent_do`) plus avoided parent compaction
(`C_compact_parent`, window-in + summary-out at parent $/token) vs brief +
re-ingest. Cap parallel `N` so reports fit remaining parent context. Cheap
or local children are the compact hedge. Extra cloud children need their
own edge. One `rg` of one tree has `C_prompt + C_reingest` larger than the
hits; do not spawn it.

## Do not

- Spawn a child to run one `rg` / `grep` / `list_dir` of one tree. Spawn
  tax plus re-ingest exceeds running the command and reading the hits.
- Inline a multi-command host procedure when a helper exists or should.
- Search several trees on the parent. Forest / multi-location search is
  **denied**; spawn or graph instead. Escape:
  `SUBAGENTS_FIRST_ALLOW_PARENT_SEARCH=1`.
- Re-read the model-routing table to pick a child model.
- Pin decompile or implementation to 8B local.

This overrides model-routing’s “skip the child for write / MCP / judgment”
when a child can do that **large** step (install+config+units, decompile,
multi-file implementation). It does not override a single search command.

| Excuse | Reality |
|--------|---------|
| “I'll spawn a child to rg this dir” | Spawn tax + re-ingest exceeds one rg; parent runs the command |
| “Faster to grep here” | Yes for one tree; spawn when the search spans several locations |
| “I need JADX in this context to verify” | Child returns the frames; parent re-runs self-test |
| “model-router says T3 stays on parent” | T3 stays on the **child** |
| “It’s not reverse engineering” | Spawn large work; not every command |
