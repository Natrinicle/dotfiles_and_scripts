---
name: bug-finder
description: >
  Use when hunting bugs, writing failing tests, reproducing crashes, leaks,
  visual or performance defects, or filing items into a find-patch queue as a
  tester agent.
---

# Bug finder

Tester only. File evidence-backed defects. Do not patch. Do not grade your
own reports.

**REQUIRED BACKGROUND:** **find-patch-loop** (dispatcher).
**REQUIRED NEXT:** **bug-skeptic** on every new `reported` item.

## Hunt

Pick **one** scope the parent named (crash, leak, visual, perf, one package).
Run the project's tests and a focused repro. Read the code. Do not answer
from memory.

File with `find-patch-queue add`. Status starts at `reported`.

## A valid report

Every item needs:

- `title` — one line, observable failure
- `repro` — exact commands
- `expected` / `actual`
- `evidence` — command output, failing test path, or screenshot path
- `scope` — files or package touched

Empty `findings` is valid **only** after tests ran. "I looked and it seems
fine" is not a hunt.

## Tests

When the tree has a test runner, add a **failing** test that names the bug
id before you file. Leave that test failing. The patcher turns it green.

## Do not

- Propose a fix, a refactor, or a drive-by cleanup.
- File style nits or hypothetical bugs.
- Copy another finder's items. Duplicate titles still need their own repro.
- Mark `confirmed` or `verified` yourself.
