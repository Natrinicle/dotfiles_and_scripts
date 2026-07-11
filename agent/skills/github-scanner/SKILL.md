---
name: github-scanner
description: >
  Pull recent GitHub commits, PR text, and review comments for style and contact analysis.
---

# GitHub Scanner

Use `gh` (authenticated) to collect recent activity on repos the user touches.

**After pull:** `style-analyzer` on user-authored text; `contact-syncer` on coworker text.  
**From `profile-updater`:** pull-only.

Cache: `~/.cache/agent-pulls/github/`. Cursor: `{MEMORY_ROOT}/github-last-pull.txt`.

## Auth

```bash
gh auth status
gh api user --jq .login
```

If unauthenticated, ask for `gh auth login` and continue without GitHub rather than failing the whole session.

## What to pull (since last cursor)

- Commits authored by the user (`gh search commits` or repo logs)  
- Open/recent PRs authored by the user — body + comments  
- Review comments and issue comments by the user  
- Coworker comments on those same PRs/issues (for contacts)  

Prefer JSON (`--json`) for stable parsing. Cap volume (e.g. last 7–14 days or last N items).

## Attribution gotchas

- Bot accounts (Dependabot, renovate, CI) → skip for style/contact  
- Distinguish **PR author** vs **reviewer** vs **commenter**  
- Commit message style ≠ PR description style — keep both, tag audience  
- Quote-replies and review suggestions still count as authored text  

## Normalize

User messages:
```json
[{"ts":"…","text":"…","source":"github","channel":"owner/repo#123","audience":"pr-description|review-comment|commit"}]
```

Coworker maps: author → list of comments with repo/PR context.

## Post-pull

Unless pull-only: style-analyzer → contact-syncer. Update last-pull date only after a successful pull.
