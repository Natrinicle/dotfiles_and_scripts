---
name: illustrated-brochure
description: >
  Create a marketing-style landscape PDF brochure with Dia flowcharts and
  Graphviz figures. Use when the user wants a colorful illustrated PDF, a
  walkthrough of a task or process, a comparison of options, an incident
  story, or a field story of original vs rewrite vs correct path. Skip for
  printable webpages, slide decks, and design-doc PDFs.
---

# Illustrated brochure

A landscape Letter PDF a stranger can finish in a few minutes. Dia for
narrative flow. Graphviz for comparison. fpdf2 for the page. Same visual
system for every subject.

This skill documents **any** requested task or process. The three-path
rewrite story is one shape, not the only shape.

## Story shapes

Pick from the request. Do not force three-path labels onto a how-to.

| Shape | Use when | Typical pages |
|-------|----------|---------------|
| **process** | How a task, procedure, or system works | 4–8 |
| **comparison** | Options side by side | 4–6 |
| **incident** | What happened, what to keep, what to do | 4–6 |
| **field-story** | Original path, a rewrite, the path to finish | 6 |

Default to **process** unless the user names competing paths or an incident.

## Page recipes

Cover always: title, one-sentence promise, overview figure. Last page always:
a score or “do this next” banner. Middle pages carry one Dia or Graphviz each.

**process** — cover; scene or dictionary if the domain needs it; one flow page
per major step or phase; close with the working sequence.

**comparison** — cover; shared scene; one page per option (right / wrong or
keep / drop); scorecard.

**incident** — cover; scene; what happened (Dia); what to keep; what to do.

**field-story** — cover; metaphor; original; first rewrite; path to finish;
scorecard. Path labels stay “original”, “first rewrite”, “path to finish”.
No personal names, product names, employer names, or repo names.

Details: `references/copy.md`.

## Visual system and diagrams

Load `references/visual-system.md` and `references/diagrams.md`. Accents are
1 / 2 / 3 (amber, rose, teal). Field-story maps those to original / rewrite /
finish. Other shapes map them to steps, options, or phases.

Helpers (copy into the project `docs/<slug>/` tree, then adapt):

- `scripts/dia_flowchart.py` — Dia 0.98 flowchart XML
- `scripts/export_diagrams.py` — SVG→PNG; Graphviz dpi 200
- `scripts/brochure_base.py` — cream page, type, cards, `page_count`

Story copy, titles, and metaphors stay in the **project**. This skill has no
product names. The PDF cover kicker is the topic or document type
(FIELD STORY, A WALKTHROUGH), never the product, employer, or repo.

## Workflow

1. Pick the shape. Name the pages before drawing.
2. If the domain is technical, pick **one** metaphor and stick to it. Teach
   the plot device on the scene page before any diagram uses it.
3. Dia for “then this happened”. Graphviz for “these sit next to each other”.
4. Build the PDF with fpdf2. Pass `page_count` to `Brochure`.
5. Raster **every** page (`pdftoppm`). Read each PNG. Fix overlap, clipping,
   and unreadably small type. See `references/verify.md`.

Output: `docs/<slug>/` in the current project (`build.py`, `diagrams/`, PDF).
The skill stays reusable; the story stays in the repo that asked for it.

## Package

This skill is a general agent skill. Resolve the destination from
`{AGENT_HOME}/config/toolkit-homes.yaml` (see `package-toolkit`). Do not
invent `{HOME}/repos/<name>-toolkit`.
