---
paths:
  - "**"
---

# Prefer subagents when the parent might compact midway

If a task could outrun the parent's remaining context before it finishes,
run it in a subagent. A parent compaction in the middle of a task loses the
working state (open files, test output, half-applied edits) and the summary
that replaces it is not a resume point. A child's compaction is the child's
problem; the parent keeps only the brief and the report.

## Trigger

Any of these before starting the work, not after the window fills:

- Multi-file implementation, a test-fix loop, or a plan task with its own
  verify cycle (rule `subagents-first`; plans run via
  `superpowers:subagent-driven-development` by default).
- A walk through a dump, tree, log, or install whose output volume is
  unknown.
- Remaining parent context is under roughly a third, and the next step is
  more than one command.
- The task would need to be told "continue" after a compact to finish.

## Do

1. Write a complete brief: paths, constraints, exact interfaces, the
   verify command, the report shape. The child does not see this window.
2. Pick model and effort via rule `model-routing` / skill `model-router`.
3. Before the parent compacts for any reason, file the pieces a later
   session needs to MemPalace (rule `mempalace-compact-filing`). The
   compact summary is not filing.
4. Parent keeps synthesis, landing approvals, and the user-facing answer.

## Do not

- Start a long task on the parent because "it is probably short".
- Treat a post-compact summary as if the half-done task were done.
- Spawn for one `rg`, one `kubectl get`, or one command piped into grep
  (rule `subagents-first` keeps those on the parent).

Cost model: skill `expected-value` (`C_compact_parent`). Dispatch shape:
rule `subagents-first`, skill `agent-graphs`.
