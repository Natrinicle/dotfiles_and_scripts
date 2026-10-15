---
name: ops-report-format
description: "Ops companion to forensic-expert-report-format. Reuse the report structure for incident reports, postmortems, and audit findings, swapping legal boilerplate for operational conclusions. Use when turning structured findings blocks into a clean write-up."
type: workflow
lifecycle: active
---

# Ops Report Format

Thin companion to `forensic-expert-report-format`.

## Core reuse

Follow the section order and tone of `forensic-expert-report-format`. Consume the same structured blocks (`TIMESTAMP_CLUES`, `BANDWIDTH_LIKELIHOOD`, `IDENTICAL_CONTENT`, etc.).

## Ops adaptations

- Replace “Expert Report / Opinions / I reserve the right…” with “Incident Report / Findings / Conclusions”.
- Drop court caption, Bates, compensation rate, and legal reservation unless needed.
- Keep: background, examination/observations, numbered findings that map to evidence.
- Add: impact, timeline, remediation, and detection gaps when relevant.

## Template

See `assets/ops-report-template.md`.

## Upstream note

Structured-block consumption and observation-to-conclusion mapping must stay compatible with the forensic report skill.
