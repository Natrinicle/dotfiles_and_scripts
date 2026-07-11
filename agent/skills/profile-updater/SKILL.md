---
name: profile-updater
description: >
  Orchestrate multi-source profile refresh across chat, issues, git, mail, and Speakr.
---

# Profile Updater

1. Run scanners in **pull-only** mode: `slack-scanner`, `jira-scanner` (if using
   Jira), `github-scanner`, `speakr-scanner`, optional `inbox-scanner`.  
2. Soft-fail per source; record skips.  
3. `style-analyzer` on merged user text with source tiers.  
4. `contact-syncer` on multi-party dirs.  
5. Summarize what changed.  

Do not commit tokens or raw pulls to git.
