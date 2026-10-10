---
name: screenshot-writing-style
description: Use when scanning, analyzing, or reading screenshot images — looks for text authored by the user and updates the writing style profile over time
---
## Subagent Model Routing

Consult `~/.claude/memory/model-routing-table.md` for model assignments. This skill has two phases:
- **Screenshot OCR** (task ID: `screenshot-ocr`) — extracting text from images, identifying who wrote what. Structured extraction, T2.
- **Style comparison** (task ID: `screenshot-style`) — comparing extracted text against writing style profile for new patterns. Nuanced judgment, T3.


# Screenshot Writing Style Tracker

## Overview

When scanning screenshots, always look for text authored by the user and compare against the saved writing style profile. Update the profile when new patterns or stylistic shifts are observed.

## When to Use

- Scanning or analyzing any screenshot images
- Reading images from a Screenshots directory
- Any task involving visual inspection of captured screens

## Enhanced Image Scanning Rules

- Always OCR text content from images — do NOT rely on filenames or metadata for descriptions
- Check for reaction emojis visible in screenshot (Slack reactions, GitHub emoji responses)
- Parse any code blocks visible in screenshots as conversation context
- Note any links visible in screenshots for additional context gathering

## Process

1. While examining screenshots for the primary task, also identify text authored by **the user** (identify by their Slack username, GitHub username, display name, or real name from ``${HOME}/.grok/skills/nate-writing-style/references/user_writing_style.md` (also `artifacts/claude/memory/user_writing_style.md`)`)
2. **Verify attribution carefully** — do NOT assume authorship. For each message:
   - Check the username/avatar label directly above or beside the message
   - In Slack, consecutive messages from the same person are grouped — a message without a name label belongs to the LAST labeled author above it, which may be someone else
   - If a conversation has multiple participants, track who is speaking at each point — do not default to attributing ambiguous messages to the user
   - When uncertain, mark the message as unverified and do NOT use it for style analysis
   - **Contextual role check**: consider who is the author vs reviewer, requester vs responder in the conversation. Messages that sound like a reviewer directing a PR author, or a manager giving instructions, are likely NOT the user unless they are clearly in that role. The user (check their role from the user profile memory) — filter accordingly.
   - **Present suspicious attributions to the user** for confirmation rather than silently adding them to the style profile
   - **AI output detection**: Messages containing structured code blocks, numbered PoC steps, or highly formatted technical output may be AI-generated content that the user is sharing — not their personal writing style. Do not use these for style analysis. Only the surrounding conversational framing (introductions, questions, follow-ups) reflects their voice.
3. When verified as the user's, transcribe messages exactly — preserve capitalization, punctuation, formatting, line breaks
4. Compare against the style profile at ``${HOME}/.grok/skills/nate-writing-style/references/user_writing_style.md` (also `artifacts/claude/memory/user_writing_style.md`)`
5. If new patterns, phrases, or stylistic shifts are observed, update the memory file — but only from verified messages

## What to Look For

- **New characteristic phrases** not already documented
- **Shifts in punctuation habits** (e.g. more/fewer trailing questions, ellipsis usage changes)
- **Changes in tone or formality** across different contexts (Slack DMs vs PR descriptions vs commit messages)
- **Formatting evolution** (how structured messages are organized)
- **Context-dependent style variations** (casual vs technical vs interpersonal)
- **Adversarial exchanges** -- when screenshots show friction, escalation, or loaded language between the user and another person

## Communication Pattern Detection

When screenshots contain adversarial exchanges or friction patterns (not just the user's writing style), invoke the `communication-pattern-analysis` skill with:
- **Contact name:** the other party identified from screenshot context
- **Source:** screenshot (include filename and directory)
- **Evidence:** transcribed quotes from BOTH parties in the screenshot
- **Pattern type:** which pattern was detected

The `communication-pattern-analysis` skill owns the file format and all writes. Do not write to pattern analysis files directly.

**Key rule:** Transcribe BOTH parties' messages from the screenshot -- never one-sided. Note constructive behaviors alongside problematic ones.

## Quick Reference

Identify the user by checking their Slack username, GitHub username, and display name from ``${HOME}/.grok/skills/nate-writing-style/references/user_writing_style.md` (also `artifacts/claude/memory/user_writing_style.md`)`.

| Style Profile Location | ``${HOME}/.grok/skills/nate-writing-style/references/user_writing_style.md` (also `artifacts/claude/memory/user_writing_style.md`)` |

## Grok import note (2026-09-02)

This skill was imported from Claude `~/.claude/skills`. Local Claude memory paths still apply on {user}'s machines. A sanitized copy of that tree lives at `${HOME}/artifacts/claude/`.
