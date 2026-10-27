---
paths:
  - "**"
---

# Local First — Ask Before Landing Actions

**Default:** do work **locally** first. Do **not** land it until the user
explicitly approves that step.

**Ask and wait** before:

- `git commit` / amend
- `git push` (any remote, including publishing a new branch)
- Opening or updating PRs in a way that publishes (`gh pr create`, etc.)
- Posting **PR/issue comments** or reviews
- **Server or cluster mutations** (SSH apply, installs, restarts, reimage,
  kubectl/Helm/compose that change state)

**Not permission to land:** “update the docs,” “document this,” “for the
repo,” “write a runbook,” “continue,” “save it.” Those mean **local file
edits only**.

**Do not wait** only when they name the landing action, e.g. “Commit and
push,” “Comment on the PR with …,” “On {host} install Longhorn / apply the
manifests.”

**Always OK without asking:** read-only inspection, local workspace edits,
drafts for the user to approve, local memory/rule notes when they asked for
a rule change.

One approval is not a blank check (commit ≠ push ≠ PR comment ≠ next server
change).

Full detail: `{MEMORY_ROOT}/feedback-ask-before-commit-push-comment-server.md`
