---
name: find-patch-loop
description: >
  Use when the user wants a multi-agent bug hunt where some agents find
  defects and others patch them, a tester-bot plus coder-bot loop, repeated
  find-fix-retest, competitive code review, or a find-patch queue.
---

# Find-patch loop

Dispatcher only. Split **find**, **skeptic**, and **patch**. One agent must
not hunt, fix, and declare victory.

**REQUIRED SUB-SKILL:** **bug-finder** for hunting and filing.
**REQUIRED SUB-SKILL:** **bug-skeptic** for proving a report or a patch wrong.
**REQUIRED SUB-SKILL:** **bug-patcher** for applying confirmed items.

Session-complete verification is **check-work**, not this loop.
The always-on rule **independent-checker** applies to every role.

## Roles

| Role | Job | Must not |
|------|-----|----------|
| Finder | Reproduce, write tests, file evidence | Patch or grade own reports |
| Skeptic | Try to refute each report or patch | Invent nits; rubber-stamp |
| Patcher | Minimal fix for one confirmed id | Grade own diff |
| Operator | Pick which confirmed items to fix | Skip the skeptic |

## Loop

1. Finder(s) fill `.find-patch-queue.json` (`find-patch-queue`). An empty list is valid only after they ran tests.
2. Skeptic on **each** new `reported` item. `false` → not a bug. A failed or
   missing skeptic is **unverified** — do not patch it.
3. Operator (or the user) marks `confirmed` vs `wontfix`.
4. One patcher per confirmed id.
5. A **different** finder or skeptic re-runs the original repro. Only then `verified`.
6. Repeat until two consecutive hunt rounds add nothing new, or the user stops.

## Parallelism

- Several finders with **different** scopes (crash, leak, visual, perf, one subsystem).
- Several skeptics, one per report.
- Patchers only after confirm. Isolated worktrees if they edit in parallel.

Grok Build: optional workflow `find-patch-loop` (hunt → skeptic → propose patches). It does not land commits.

## Stop

- Two dry hunt rounds.
- User says stop.
- Repro needs hardware the agent cannot reach — file `needs-info`, do not fake it.

## Do not

- Fix from a report with no command output, failing test, or screenshot path.
- Let the finder spawn as its own skeptic.
- Treat "looks good" or a compile as a verified fix.
- Land commits or server changes unless the user named that step.
