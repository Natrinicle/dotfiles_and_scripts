---
name: jira-scanner
description: >
  Pull recent Jira comments and descriptions for writing-style and contact
  analysis via acli (or equivalent). Invokes style-analyzer and contact-syncer.
---

# Jira Scanner

Collect recent Jira activity, normalize it, then hand off to shared analysis
skills. Jira is a **structured** audience mode (async, ticket-shaped)—distinct
from chat.

When `profile-updater` calls this skill, run **pull-only** (no analysis).

## Auth (gotcha: non-blocking)

Prefer Atlassian CLI `acli`:

```bash
acli jira workitem search \
  --jql "assignee = currentUser() AND status != Done" \
  --fields "key,summary" --limit 1
```

If auth fails:

1. Attempt the workspace’s usual re-auth flow (site login / `acli` auth skill)  
2. If still blocked, **skip Jira entirely** and say so — chat/git still matter;
   Jira is supplementary  

Never hang a morning triage or profile refresh on a dead Jira session.

## Pull window

Use about **7 days** of `updated` activity (wider than incremental chat pulls).
Ticket comments arrive late; a one-day window misses them.

```bash
acli jira workitem search \
  --jql "assignee = currentUser() AND updated >= -7d ORDER BY updated DESC" \
  --fields "key,summary,status" --limit 20 --json
```

For each key:

```bash
acli jira workitem comment list {key} --json
acli jira workitem view {key} --json
```

## Normalize & store

Cache dir: `~/.cache/agent-pulls/jira/` (or legacy `~/.firecrawl/jira/`).

| File | Contents |
|------|----------|
| `jira-my-comments.json` | Comments by the current user |
| `jira-my-descriptions.json` | Descriptions where user is reporter |
| `jira-coworker-comments.json` | Others’ comments, grouped by author |
| `jira-tickets.json` | Key, summary, status, priority |

User message shape (shared with other scanners):

```json
[{
  "ts": "ISO-8601",
  "text": "comment body",
  "source": "jira",
  "channel": "PROJ-123",
  "audience": "ticket-comment"
}]
```

Descriptions use `audience: "ticket-description"`.

Track last success in `{MEMORY_ROOT}/jira-last-pull.txt` (date only is fine).

## Dedup against chat (gotcha)

People paste the same text into tickets. Before style analysis, drop or down-weight:

- Links back to chat archive URLs  
- Quoted blocks that match recent chat pulls  
- Near-identical bodies in both systems within ~24h  

Otherwise frequency stats and “audience modes” double-count one thought.

## Issue keys in other skills

When Speakr (or chat) mentions keys, use the same CLI:

```bash
acli jira workitem search --jql "key = PROJ-123" --fields "key,assignee"
```

Ticket **assignee** is a medium-confidence speaker-ID signal only when the
spoken content is about *doing that work*, not when the key is casually named.

Key patterns are site-specific (`PROJ-\d+`, numeric-only keys, etc.). Configure
regexes in memory if defaults miss your site—do not bake one employer’s
prefixes into the skill as universal truth.

## Post-pull analysis

Unless pull-only:

1. `style-analyzer` ← my comments (+ descriptions)  
2. `contact-syncer` ← whole jira pull dir  

Expect a more formal register than chat: fewer jokes, more links to PRs and
sibling tickets. That is an audience mode, not “the user got colder.”

## Failure modes

| Symptom | Response |
|---------|----------|
| Empty search but web UI has data | Wrong site/cloud; re-auth or set site id |
| Rate limits | Narrow JQL, sleep, smaller `--limit` |
| Huge description HTML | Strip markup before style analysis |
| Permission errors on comment list | Note ticket key; continue others |
