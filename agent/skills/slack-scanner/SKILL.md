---
name: slack-scanner
description: >
  Pull recent Slack messages for writing style, contacts, and commitments.
  Handles browser-session auth, multi-strategy API pull, and analysis handoff.
---

# Slack Scanner

Pull recent workspace chat via the Slack Web API, then hand off to analysis skills.

**After a normal pull:** run `style-analyzer` (user outbound) and `contact-syncer` (inbound).  
**When called from `profile-updater`:** **pull-only** — skip analysis; the orchestrator runs it after all sources.

Prefer cache dir `~/.cache/agent-pulls/slack/` (or existing `~/.firecrawl/slack/` if present).  
Last successful day: `{MEMORY_ROOT}/slack-last-pull.txt`.

## Authentication

Session auth needs both:
- `xoxc-…` token  
- `xoxd-…` cookie (`d=` cookie value, URL-decoded)

They expire often. Store verified credentials in a local file such as `/tmp/slack-scraper/auth.json` (not in git).

### Refresh via Chrome DevTools MCP

**Do not kill or relaunch Chrome.** Reuse the MCP-managed browser.

1. `list_pages` — prefer an existing `*.slack.com` tab; else open the workspace URL (user’s normal host).  
2. If SSO/login appears, ask the user to finish login in that window, then reload.  
3. `list_network_requests` (fetch/xhr) → first successful `*.slack.com/api/*` → `get_network_request`.  
   - Token: form/body field `token` (`xoxc-`)  
   - Cookie: request `cookie` header, `d=xoxd-…` (decode)  
4. If SPA cache shows no API traffic: navigate `about:blank`, then back to the workspace, retry.  
5. Verify with `auth.test` (Bearer + `Cookie: d=…`). On `invalid_auth`, re-extract.

If `/tmp/slack-scraper/auth.json` already validates, skip extraction.

Optional PATH helper: `slack-auth-check` when installed from this pack’s `bin/`.

## API gotchas (do not trust search alone)

1. **`search.messages` under-reports**, especially DMs — no error when truncated.  
2. **Search misses whole DM channels** that `client.counts` still lists.  
3. **Always paginate** search (`messages.paging.pages`, 1-indexed `page`).  
4. **`after:YYYY-MM-DD` is exclusive** — for “since last pull day”, use last_pull **minus one day**.  
5. **`conversations.history` omits thread replies** — for any message with `reply_count > 0` (DMs) or channel threads (`thread_ts` ≠ `ts`), call `conversations.replies`.  
6. **DM threads often hold most of the conversation** — skipping replies loses the majority of text.

### Multi-strategy pull (required)

1. `client.counts` → discover active DMs / MPIMs  
2. `conversations.history` per active DM (authoritative)  
3. `conversations.replies` for every history message with replies  
4. Paginated `search.messages` for channel discovery (`from:me` / mentions)  
5. Replies for channel threads  
6. Cross-check counts (search vs history+threads); log gaps  

Resolve identities with `users.info` before assuming display names.

## Incremental window

Read `{MEMORY_ROOT}/slack-last-pull.txt`. Build search `after:` from yesterday of that date. After success, write today’s date.

## When to invoke analysis

| Condition | Invoke |
|-----------|--------|
| Any outbound user messages | `style-analyzer` |
| Any inbound from others | `contact-syncer` |
| Pull-only orchestrator | neither |

Never skip contact-syncer solely because the user sent nothing — inbound-only batches still update contacts and commitments.

## Message scanning while analyzing

- OCR image attachments (filenames lie)  
- Parse code blocks as context  
- Note reactions as weak signals  
- Follow links; use `gh` for GitHub URLs
