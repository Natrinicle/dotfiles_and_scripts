---
name: thread-screenshots-github
description: >
  Screenshot GitHub PR review threads and issue discussions via browser automation.
---

# GitHub Thread Screenshots

## Navigation

- Open the review or issue permalink (include discussion/comment anchors when possible).  
- Wait for the target thread, not just `networkidle`.  
- Sticky PR headers cover content — scroll the **comment container**, or offset scroll
  so the target is below the sticky bar before capture.  

## Capture

- Prefer the thread element (conversation block), not the full page, when stable.  
- Expand “outdated” / hidden replies if the evidence needs them.  
- Match user theme preference when known (light/dark).  

## Safety

Read-only: no approve/request-changes/submit clicks unless the user explicitly asks
for a non-screenshot action (out of scope for this skill).
