---
name: contact-syncer
description: >
  Update contact profiles, detect friction patterns, and scan commitments from any
  message pull directory. OS address-book sync is out of scope.
---

# Contact Syncer

Consume a pull directory from chat, issues, mail, or Speakr. Update people
knowledge; do not own communication-pattern file formats (that is
`communication-pattern-analysis`).

## When to run

Whenever a pull has **any inbound** messages from others — even with zero
outbound. Never skip because “the user didn’t write anything.”

## Confidence tiers

| Tier | Sources | Use |
|------|---------|-----|
| T1 | Chat, issue trackers | Authoritative for style/friction |
| T2 | Email | High; watch forwards |
| T3 | Screenshots | Tag as verify |
| T4 | Speakr | Tag as verify; spoken ≠ written style |

Do not overwrite a solid T1 style note with T4-only evidence. Spoken promises
from Speakr become commitments only when tagged “confirm in writing.”

## Input files (read what exists)

Examples: `update-my-messages.json`, DM histories, `user-cache.json`,
coworker issue comments, Speakr coworker segments, channel counts.

## Profiles

For people with enough signal in the window:

- Create or update role, topics, interaction frequency, style notes under
  `{MEMORY_ROOT}` or project memory  
- Cross-medium: formal in tickets vs terse in chat is a signal  
- Deduplicate by platform user id, real name, display name before creating  
- Resolve chat identities with the platform user API when available  
- Preserve hand-written notes; append dated observations  

Do **not** write to desktop address books or platform-specific contact UIs from
this skill. Export/sync is a separate user choice outside this pack.

## Friction → other skills

If 2+ friction patterns appear (ignored compliance, silence on direct asks,
goalpost moves, loaded language, etc.), call `communication-pattern-analysis`
with contact, source, quotes, pattern type. Escalating cases may also need
`adversarial-analysis`. **Do not write pattern analysis files yourself.**

## Commitments

Scan user text for promises and others’ redirects (“I’ll comment on the PR”).

**Gotcha:** cheap local models mis-file open vs done. Always verify:

1. Dedup open vs completed  
2. Search later messages for follow-through  
3. For redirects, check the target medium (`gh`, issue CLI, mail) before
   “no follow-through”  
4. Resolve relative dates against a real calendar or dated messages  

Present only after verification.
