---
name: forensic-expert-report-format
description: "Structure and draft digital-forensics expert reports in the style of litigation reports used in state criminal cases. Use when turning timestamp, bandwidth, registry, or other forensic findings into a formal expert report with qualifications, background, observations, and numbered opinions. Chain after analysis skills."
type: workflow
lifecycle: active
---

# Forensic Expert Report Format

Produce a clean, court-ready expert report. Follow the section order and tone of standard digital-forensics expert reports. Accept structured findings (TIMESTAMP_CLUES, BANDWIDTH_LIKELIHOOD, or free-form notes) as input.

## Required Sections (in order)

1. **Title block** — Expert Report of [Name], Re: [Case], Court, Case No., Date.
2. **Statement of Qualifications** — Name, firm, education, certifications, relevant experience, prior testimony (list dates/cases), compensation rate.
3. **Case Background**
   - Materials reviewed (Bates ranges if known).
   - Relevant period.
   - Relevant files (table or figure).
4. **Examination and Observations**
   - Examination process.
   - Notes on date-time stamps (precision, spoliation, copy semantics).
   - Specific findings (drive reformat claims, install dates, folder identity, USB devices, etc.).
5. **Opinions** — Numbered, each beginning “In my expert opinion…” or “It is my opinion that…”. Limit to conclusions supported by the observations.
6. **Reservation / Signature block** — “I reserve the right to supplement…”, date, location, signature line.

## Style Rules

- Use numbered headings and lettered sub-headings.
- Refer to figures and Bates numbers.
- Footnotes for technical asides (precision differences, version history).
- Neutral, precise language. Distinguish observation from opinion.
- Do not invent metrics, hash values, or dates not supplied in the findings.
- When findings include TIMESTAMP_CLUES or BANDWIDTH_LIKELIHOOD blocks, incorporate them into the Observations and cite them as the basis for Opinions.

## Workflow

1. Collect expert identity, case caption, and any structured findings blocks.
2. If findings are missing, request the minimum needed (relevant period, file list, key timestamp observations).
3. Draft using the template in `assets/report-template.md`.
4. Insert observations derived from the analysis skills.
5. Derive 3–5 concise opinions that map directly to the observations.
6. Output the full report in Markdown (convertible to PDF/DOCX).

## Template

See `assets/report-template.md` for the skeleton. See `references/example-opinions.md` for opinion phrasing drawn from typical findings.

## Companions

- `ops-report-format`

Server-admin thin companions exist and should be preferred when the context is operational rather than purely forensic. When updating this skill, verify compatibility with all companions and other callers; split only if needs have diverged, with a convergence plan.
