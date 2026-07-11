---
name: thread-screenshots
description: >
  Orchestrate end-to-end screenshots of conversation threads for evidence or archives.
---

# Thread Screenshots

Coordinate capture of long threads from web UIs.

1. Prefer permalinks from APIs when available.  
2. Delegate host-specific steps to `thread-screenshots-github` or
   `thread-screenshots-slack` (or equivalent chat host).  
3. Organize outputs under a dated directory; write a short index (who/when/url).  
4. Never type into compose boxes; never send messages.  
5. Handle auth walls by asking the user to complete SSO in the automation browser.
