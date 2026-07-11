---
name: morning-summary
description: >
  Morning triage across mail, chat, PRs, issue trackers, optional calendar, and
  Speakr action items into a short prioritized list.
---

# Morning Summary

Build one action list without drowning the parent context. Dispatch heavy pulls
to subagents; keep synthesis on a capable model.

## Step 1 — Bundle status (preferred)

If available on PATH, run `morning-data-gather` (from this pack’s `bin/`). It
emits labeled sections, for example:

- GitHub user / open PRs / review requests (or `AUTH_FAILED`)  
- Issue-tracker auth (`OK` / expired / missing CLI) when Jira/`acli` is used  
- Chat auth (`OK` / expired / no token) when Slack helpers are used  
- Calendar block: content from `CALENDAR_CMD` or `CALENDAR_ICS_URL`, else
  `CALENDAR_UNAVAILABLE`  
- Optional Speakr action-item file paths if present in memory  

**Soft-fail by source:** missing auth skips that source with a note; do not abort
the whole morning.

### Calendar (generic)

Do **not** assume a desktop calendar app. Prefer, in order:

1. Output already in `=== CALENDAR ===` from `morning-data-gather`  
2. `CALENDAR_CMD` — any command the user configured  
3. `CALENDAR_ICS_URL` — published ICS feed  
4. Skip with “no calendar source configured”  

## Step 2 — Refresh weak auth only when needed

- **If using Slack** and auth expired → `slack-scanner` credential refresh  
- **If using Jira** and CLI auth expired → re-auth for that CLI, then continue  
- **If using GitHub** and `gh` failed → ask for `gh auth login`  

## Step 3 — Parallel pulls

Dispatch independent scanners (pull-only when they support it):

- Mail: `inbox-scanner` (optional light pass; IMAP/provider-agnostic)  
- Chat: `slack-scanner` when relevant  
- Issues: `jira-scanner` if using Jira  
- Speakr action items already written by `speakr-manage` (prefer file over re-ASR)  
- Open PRs / review requests via `gh`  

## Step 4 — Present

Prioritized checklist in the user’s voice (`user_writing_style.md`):

1. Blocking asks / today deadlines (include calendar lines if any)  
2. PR reviews and merge blockers  
3. Ticket pings  
4. Commitments still open (from `contact-syncer` if run)  
5. FYI noise (collapsed)  

State which sources were skipped and why.
