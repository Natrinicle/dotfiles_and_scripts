---
paths:
  - "**"
---

# Subagents first

When a step can be finished in a child session, spawn it (`spawn_subagent`).
The interactive parent orchestrates, summarizes, and verifies only where
necessary.

## Spawn for

- Decompile, protocol recovery, JADX/Ghidra/REA, unpack
- Code/file exploration, architecture mapping, large-file extract
- Implementation, packing, README, tests, lint, palace filing
- Parallel independent slices (one child per slice)

## Parent keeps

- Asking the user; landing approvals (commit / push / server)
- Synthesizing child reports into the user-facing answer
- Verification the user named, or a second look at child claims
  (self-test, residual-identity, palace search-verify, pre-commit)

## Spawn how

1. Put every path, constraint, and skill name in the child prompt. Children
   do not see this conversation.
2. Omit `model` so `[subagents.models]` pins apply. Do not load skill
   `model-router` or the routing table before spawn.
3. File-search / extract → `explore` / `code-explorer`.
4. Implementation, decompile, protocol judgment → `general-purpose` (cloud;
   do not pin to 8B local).
5. Several independent slices → spawn in parallel.

## Do not

- Do child-capable work on the parent because “context is already here”.
- Re-read the model-routing table to pick a child model.
- Pin decompile or implementation to 8B local.

This overrides model-routing’s “skip the child for write / MCP / judgment”
when a child can do that step.

| Excuse | Reality |
|--------|---------|
| “Faster to grep here” | Parent compaction costs more than a child. |
| “I need JADX in this context to verify” | Child returns the frames; parent re-runs self-test. |
| “model-router says T3 stays on parent” | T3 stays on the **child**. |
| “It’s not reverse engineering” | Offload every step a child can finish. |
