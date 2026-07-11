---
name: inbox-scanner
description: >
  Triage email inboxes (Gmail and other providers) for spam, noise, and action
  items; suggest server-side filters when the provider supports them.
---

# Inbox Scanner

On-demand mail triage via whatever access the host has: local MUA export,
IMAP CLI, or provider API. Works for **Gmail and non-Gmail** accounts.

## Account model

1. Enumerate configured accounts (Google, Microsoft, Fastmail, corporate IMAP, …).  
2. For each, scan the primary inbox.  
3. **If using Gmail (or Google Workspace):** also consider the **Important**
   (or priority) mailbox when the access method exposes it — Gmail can hide
   Important-only mail from INBOX.  
4. **If not Gmail:** skip Gmail-specific folders; still scan Inbox and any
   Focused/Priority folder if present.  
5. Deduplicate by **Message-ID**. Tag source: `inbox` | `important` | `both` | `priority`.

Never assume a single hard-coded account name or a desktop-only mail client.

## Categorize

**Keep (actionable)**  
- Direct human mail to the user  
- PRs where the user is author or requested reviewer (verify with `gh`)  
- Future calendar invites not declined (if invite data is available)  
- Issue-tracker updates that clearly need the user  
- Follow-through on a promise made in chat  

**Auto-archive (only when verified)**  
- Forge notifications where user is neither author nor reviewer  
- Notifications for already merged/closed PRs the user is not in  
- CI noise on others’ branches  
- Past calendar events / declined invites when that state is known  

Verify GitHub involvement before auto-archive:

```bash
gh api user --jq .login
gh pr view {n} --repo {owner}/{repo} --json author,state,reviewRequests
```

Use the real `owner/repo` from the notification.

**Confirm before archive**  
- Reviewer on a closed PR, long threads not mentioning the user, etc.

**Spam / marketing**  
- Newsletters, vendor blasts — propose filters after patterns repeat.

## Message scanning

Apply shared message-scanning rules: OCR attachments, parse code, follow links,
note new people for contact-syncer (memory profiles only).

## Filters (provider-specific)

### If using Gmail
- Suggest filters only after ~5+ similar noise messages.  
- **`from:` must be copied from real headers**, never guessed.  
- Use only supported operators (`from:`, `to:`, `subject:`, `list:`, …).  
- Combine `subject:` phrases with body keywords so filters are not over-broad.  
- Tell the user to test the query in Gmail search before saving.  

### If using another provider
- Describe the pattern in plain language (sender domain, subject tokens).  
- Map to that provider’s rule UI/API when known; otherwise give copy-paste criteria.  
- Same rule: never invent sender addresses.

## Cross-channel

If mail shows friction patterns, invoke `communication-pattern-analysis` with
evidence. Do not write pattern files yourself.

## Report

Counts by mailbox, kept/auto-archived/pending, Important-only finds (Gmail),
suggested filters, new contacts for memory, notable OCR/link context.
