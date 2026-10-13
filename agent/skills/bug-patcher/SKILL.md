---
name: bug-patcher
description: >
  Use when applying a confirmed bug from a find-patch queue, after a skeptic
  has accepted the report, before claiming a fix is done.
---

# Bug patcher

Coder only. Fix **one** confirmed queue id. Do not hunt new bugs in this
spawn. Do not declare the fix verified.

**REQUIRED BACKGROUND:** **find-patch-loop**.
**REQUIRED NEXT:** **bug-skeptic** (or a fresh finder) re-runs the original
repro.

## Gate

Work only on items with status `confirmed`. If the skeptic verdict is
missing, `false`, or `needs-info`, stop and send it back.

```bash
find-patch-queue show BUG-001
find-patch-queue set BUG-001 --status patching
```

## Patch

- Smallest change that makes the filed repro pass.
- Keep the finder's failing test. Make it pass. Do not delete it.
- Do not expand into adjacent cleanup, features, or unrelated files.
- Isolated worktree when another patcher is running.

Then `find-patch-queue set BUG-001 --status patched` and paste the diff
summary plus the test command you ran.

## Do not

- Mark `verified`. That is a different agent.
- "Fix" a report that has no evidence.
- Rewrite the module because the bug was nearby.
- Commit, push, or apply to a server unless the user named that step.
