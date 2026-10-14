---
paths:
  - "**"
---

# Employer org PR findings gate

Hard gate. Before `gh pr create`, pushing a branch that opens a PR, or
declaring an existing PR ready in the **current employer's GitHub org**:

1. Read `{MEMORY_ROOT}/employer-pr-findings-gate.md`.
2. Run **pre-commit-gate** when a pre-commit config exists (follow findings
   or prompt; do not skip).
3. Run the checklist on the actual diff (secrets, CI secret-scan footguns,
   compose/image/auth exposure, CWE classes via **cve-catalog**).
4. If you authored the change, spawn a **different** agent (**independent-checker**,
   `security-auditor` when available) to grade it.
5. Do **not** open or update the PR until every applicable item is PASS or an
   explicit waiver is in the PR body (what, why, blast radius).

CI green is not this gate. Landing still follows **ask-before-remote-actions**.

Open PRs you already authored: run the same checklist before calling them done.
