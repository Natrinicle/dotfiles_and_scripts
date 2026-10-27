---
name: screenshot-writing-style
description: Use when scanning, analyzing, or reading screenshot images — looks for text authored by the user and updates the writing style profile over time
---

# Screenshot Writing Style Tracker

When scanning screenshots, look for text authored by the user and compare
against the saved writing style profile. Update the profile when new patterns
or stylistic shifts are observed.

OCR phases may consult `{MEMORY_ROOT}/model-routing-table.md` when that table
exists (`screenshot-ocr`, `screenshot-style`).

## When to Use

- Scanning or analyzing any screenshot images
- Reading images from a Screenshots directory
- Any task involving visual inspection of captured screens

## Image scanning

- Always OCR text content from images. Do not rely on filenames or metadata.
- Check for reaction emojis visible in the screenshot.
- Parse any code blocks visible in screenshots as conversation context.
- Note any links visible in screenshots for additional context.

## Process

1. Identify text authored by **the user** (Slack username, GitHub username,
   display name, or real name from
   `{AGENT_SKILLS}/nate-writing-style/references/user_writing_style.md` and
   `{MEMORY_ROOT}/user_writing_style.md`).
2. **Verify attribution.** Do not assume authorship. For each message:
   - Check the username/avatar label directly above or beside the message.
   - Consecutive messages from the same person are often grouped. A message
     without a name label belongs to the last labeled author above it.
   - If a conversation has multiple participants, track who is speaking.
   - When uncertain, mark the message as unverified and do not use it for
     style analysis.
   - Messages that sound like a reviewer directing a PR author, or a manager
     giving instructions, are likely not the user unless they are clearly in
     that role.
   - Present suspicious attributions to the user for confirmation.
   - Structured code blocks, numbered PoC steps, or highly formatted technical
     output may be AI-generated content the user is sharing. Use only the
     surrounding conversational framing for style.
3. When verified as the user's, transcribe messages exactly: capitalization,
   punctuation, formatting, line breaks.
4. Compare against the style profile at
   `{AGENT_SKILLS}/nate-writing-style/references/user_writing_style.md` and
   `{MEMORY_ROOT}/user_writing_style.md`.
5. If new patterns, phrases, or stylistic shifts are observed, update the
   profile from verified messages only.

## What to look for

- New characteristic phrases not already documented
- Shifts in punctuation habits (trailing questions, ellipsis usage)
- Changes in tone or formality across contexts
- Formatting evolution
- Adversarial exchanges: friction, escalation, or loaded language

## Communication pattern detection

When screenshots contain adversarial exchanges or friction patterns, invoke
`communication-pattern-analysis` with contact name, screenshot source,
transcribed quotes from **both** parties, and pattern type. That skill owns
the file format and all writes.

## Quick reference

| Style profile | `{AGENT_SKILLS}/nate-writing-style/references/user_writing_style.md` |
| Live profile | `{MEMORY_ROOT}/user_writing_style.md` |
