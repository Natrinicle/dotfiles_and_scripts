---
name: thread-screenshots-slack
description: >
  Screenshot Slack channel or DM threads via browser automation with SSO-safe habits.
---

# Chat Thread Screenshots (Slack-class)

## Auth

- Reuse existing workspace session in the automation browser.  
- If SSO intervenes, pause for the user; do not automate password entry.  
- **Never kill the browser** to “fix” auth.

## Finding the thread

- Prefer API-derived permalinks (`message ts` → archive URL).  
- After load, ensure the **thread panel** (or correct channel history) is focused.  
- Desktop web apps often steal scroll — scroll inside the message list, not the window only.  

## Hard rules

- **Never focus or type in the message compose box.**  
- Dismiss “open in app” / download promos without clicking destructive actions.  
- Capture thread replies fully; parent-only screenshots miss the decision.  

Same composition rules as other thread skills: dated files + short index.
