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
operands, unpiped `rg`/`grep` with no path). A single `rg` / `grep` /
`find` / `list_dir` of **one** tree (including a git repo root) stays on
the parent. A grep-family filter of stdin (`ss | grep 11434`,
`git show … | grep version`) stays on the parent.

## Shape (do not collapse)

| Work | Run |
|------|-----|
| One command (`rg`, `grep`, `list_dir` of one tree) | Parent |
| One command piped into grep (`ss \| grep 11434`) | Parent |
| Existing helper script | Parent (`prefer-helper-scripts`) |
| More than one command, or reusable multi-grep diagnostics | Prefer a helper script; spawn only if the work is still large |
| Discovery loop (many rg/read/strings/jadx/Ghidra/REA in one dump or several trees) | Spawn. Parent compact is the cost. |
| One large child-capable unit | `spawn_subagent` |
| Several units that do not consume each other's output, or a gate / named output between steps | skill **agent-graphs** (workflow `agent-graph`). Inner retry is **loop-until-green**. |
| Bug hunt | **find-patch-loop** |
| Session-complete verify | **check-work** |

Do not grow this rule into graph topology. Do not dump several trees into
the parent “so the graph has context”.

## Spawn for

- Software install that includes config and service files
- Search across multiple locations (`$HOME`, `~/repos`, several trees)
- Discovery loops: many searches, reads, or commands through a dump or tree
  (jadx out, `libapp.so`, firmware, unpack dirs) even when the path is one
  tree. One `rg` stays here; a walk that would fill this window does not.
- Decompile, protocol recovery, JADX/Ghidra/REA, unpack
- Architecture mapping, large-file extract
- Multi-file implementation, packing, README, tests, lint, palace filing
- Parallel independent slices (one child per slice)

## Parent keeps

- Single commands: `rg`, `grep`, `find` of one tree, `list_dir`, `git status`
- One-shot pipes into grep (`ss | grep 11434` to verify a port opened)
- Calling an existing helper; writing one when the sequence is more than a
  single command **and** looks useful later (`prefer-helper-scripts`)
- Asking the user; landing approvals (commit / push / server)
- Synthesizing child reports into the user-facing answer
- Verification the user named, or a second look at child claims
  (self-test, residual-identity, palace search-verify, pre-commit)

## Spawn how

1. Put every path, constraint, and skill name in the child prompt. Children
   do not see this conversation.
2. **Every spawn uses model-routing.** Rule `model-routing` plus skill
   `model-router` pick the task id, tier, model, and effort. Do not inherit
   the parent by default. Do not pick a model from habit.
   - Pinned light types (`explore`, `code-explorer`, `local-search`,
     `local-extract`): omit `model` so host `[subagents.models]` pins apply
     (T0). Skip re-reading the full table for those pins.
   - Dump harvest, decompile, protocol recover, unpinned cloud children:
     load skill `model-router`, look up the task id, pass that `model`
     (and effort when the spawn tool has it). This preference counts as
     requesting a model for those tasks.
3. File-search of **source trees** → native `explore` / `code-explorer` when
   the harness offers those types. **Grok Build does not:** `spawn_subagent`
   only lists plugin types. Dump harvest: omit `subagent_type` (cloud
   general-purpose) with the T2 model from `model-router`. Do not use
   `feature-dev:code-explorer` with `ollama-gemma4` (16K window vs ~24K
   plugin inject).
4. Implementation, decompile, protocol judgment → `general-purpose` at the
   **model-router** tier (dump-harvest / protocol-recover are T2). Do not
   pin those to 8B local.
5. Several independent slices → spawn in parallel.

Every spawn scores **context-window** EV (skill `expected-value`): parent
tokens saved (`C_parent_do`) plus avoided parent compaction
(`C_compact_parent`, window-in + summary-out at parent $/token) vs brief +
re-ingest. Cap parallel `N` so reports fit remaining parent context. Cheap
or local children are the compact hedge. Extra cloud children need their
own edge. One `rg` of one tree, or one command piped into grep, has
`C_prompt + C_reingest` larger than the hits; do not spawn it.

## Model and effort (skill `model-router`)

| Task | Tier | Effort | Do not |
|------|------|--------|--------|
| Pinned source-tree explore / T0 extract | T0 local | n/a | |
| Dump harvest, jadx, firmware strings, protocol recover | T2 | **high** | parent **xhigh**, Fable, Opus, Haiku, gemma4, effort **low** |
| Adversarial / PII / style / architecture critic | T3 | xhigh only when that judgment is the task | file/dump search |

File/dump search does not need xhigh or Fable. Haiku / gemma4 miss GATT,
opcodes, and device lists. Full ids: `dump-harvest`, `protocol-recover` in
`{MEMORY_ROOT}/model-routing-table.md`.

**Ollama overloaded:** T0 pin is allowed to fail over to the **lowest
upstream** tier (T1). Claude: Haiku. Grok: cheapest cloud slug in the spawn
enum that is **not** the xhigh parent session id and **not** another Ollama
id (`grok-4.7` default **high** on this host). Retry 503 once; then T1 is
allowed. A slow VRAM load is not overload. `litellm-gemma4` still hits
Ollama — skip it on overload.

## Do not

- Spawn a child to run one `rg` / `grep` / `list_dir` of one tree, or
  `ss | grep` / `git show | grep`. Spawn tax plus re-ingest exceeds
  running the command and reading the hits.
- Inline a reusable multi-command host procedure when a helper exists or
  should (router iptables/clients/stats). A one-shot verify stays here.
- Search several trees on the parent. Forest / multi-location search is
  **denied**; spawn or graph instead. Escape:
  `SUBAGENTS_FIRST_ALLOW_PARENT_SEARCH=1`.
- Walk a dump (jadx, `libapp.so`, firmware) on the parent because it is
  “one tree”.
- Skip `model-router` for dump-harvest because of the Grok T0 short-circuit.
- Pass the parent session model id when that session is **xhigh** (the child
  inherits xhigh).
- Pin decompile, dump harvest, or implementation to 8B local or Haiku.

This overrides model-routing’s “skip the child for write / MCP / judgment”
when a child can do that **large** step (install+config+units, decompile,
multi-file implementation). It does not override a single search command.

| Excuse | Reality |
|--------|---------|
| “I'll spawn a child to rg this dir” | Spawn tax + re-ingest exceeds one rg; parent runs the command |
| “Faster to grep here” | Yes for one tree; spawn when the search spans several locations |
| “It's one jadx tree so I'll grep here” | Discovery loop fills the parent; spawn |
| “I need JADX in this context to verify” | Child returns the frames; parent re-runs self-test |
| “model-router says T3 stays on parent” | T3 stays on the **child** |
| “Grok says omit model” | That is the T0 pin. Dump harvest is T2 via model-router |
| “xhigh / Fable will find more strings” | File/dump search is T2 **high**, not T3 |
| “Haiku is cheaper for search” | Missed opcodes corrupt the pack; T2 |
| “Ollama 503, keep the parent on xhigh” | T1 lowest upstream is the allowed fallback |
| “It’s not reverse engineering” | Spawn large work; not every command |
