# Agent Skills Toolkit

Sanitized package of agent skills (Grok/Claude compatible).

## Contents

- 50+ skills covering writing style, communication pattern analysis, scanners (Slack/Jira/GitHub/email), domain tools (IR protocols, DNS, court monitoring, etc.), and workflow helpers.
- **Writing style**: `nate-writing-style` with multi-party isolation rule (group chats must not blend other voices into personal style).
- **Screenshot style tracker**: careful attribution required.

## Install

1. Copy the directory tree into `${HOME}/.grok/server-skills/` or your agent skills path.
2. Adapt placeholders (`{user}`, `{company}`) in personal skills if reusing for someone else.
3. Personal skills (`nate-writing-style`, `resume-tailor`) are voice-specific; review before sharing further.

## Placeholders

- `{user}` — replace with your name/handle
- `{company}` — replace with organization names
- `${HOME}` — home directory

## Vendor-specific bits

Skills that call `gh`, Slack, Jira, etc. keep CLI names. Org/channel IDs are abstracted where possible.

## Residual scan notes

Personal style reference files intentionally retain example phrasing. Other files have been sanitized for common identifiers. Re-scan if redistributing.
