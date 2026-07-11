---
name: style-analyzer
description: >
  Update user_writing_style.md from chat, issue trackers, email, Speakr, or screenshots.
---

# Style Analyzer

Write durable voice notes to `{MEMORY_ROOT}/user_writing_style.md`.

## Input

Normalized messages:
```json
[{"ts":"…","text":"…","source":"slack|jira|email|github|speakr|screenshot","channel":"…","audience":"…"}]
```

Merge multi-file corpora when the caller passes several paths.

## Confidence

| Tier | Source | Notes |
|------|--------|------|
| Highest | Chat, Jira/issues, email, git | Typed, attributed |
| Medium | Screenshots | OCR risk |
| Lower | Speakr | ASR + diarization |

Reinforce across tiers; Speakr-only audience modes stay **provisional**.  
Never promote um/uh fillers into written style unless they appear in typed text.

## What to capture

Capitalization, punctuation, list habits, humor, hedging, greeting/sign-off,
technical density, how formality shifts by audience (chat vs tickets vs email vs
meetings).

Always update the profile file when invoked. Prefer additive, dated notes over
deleting prior truth.
