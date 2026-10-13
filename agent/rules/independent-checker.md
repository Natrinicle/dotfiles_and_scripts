---
paths:
  - "**"
---

# Independent checker

The agent that produced a claim does not grade it.

- Finder reports are not bugs until a **different** agent (or the user) confirms them.
- Patcher diffs are not "fixed" until a **different** agent re-runs the repro.
- `check-work` is a different spawn from the implementer.
- "I just wrote it, it looks fine" is not evidence.
- A failed or missing checker is unverified, not a pass.

Use **find-patch-loop** when several agents hunt and others patch.
Use **bug-skeptic** to refute a report or a patch.
Use **check-work** to verify a whole session.
