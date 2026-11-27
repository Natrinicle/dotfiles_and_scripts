---
name: formbook
description: Analyze, use, or contribute to davidawad/formbook — open Typst court-filing templates for markdown-first lawyers. Triggers on formbook, court filing templates, Typst legal briefs, markdown to court PDF, CourtListener court id templates, open formbook, Lexis forms alternative, or agent-generated court documents.
---

# formbook

Open collection of court-filing templates (Typst primary, some LaTeX/DOCX).  
Write substance in Markdown + YAML frontmatter; template produces a PDF matching the court's rules (caption, TOC/TOA, margins, fonts, certificates, pleading paper, etc.).

**Repo:** https://github.com/davidawad/formbook  
**Status (v0.2.0, late 2026):** ~1,185 Typst template folders across ~376 courts (all federal including SCOTUS + bankruptcy, many state). Machine-checked against real filed exemplars. **No court is human-verified / marked done yet.** Author is recruiting licensed attorney reviewers.

## Key facts

- Organized by CourtListener court ID.
- Every template has a real public filed exemplar PDF + SOURCE.md, sample Markdown input, rendered output, and overlay tools (`just overlay`).
- "Up for review" = machine-checked (rules.md from primary sources, warning-free render, layout checks, no copied sample text). Not attorney-signed.
- Typst is the reference engine. DOCX is best-effort (pleading-paper line numbering is imperfect in Word).
- Built largely by a fleet of coding agents; contribution loop is designed for agents.
- GPL v3. Not legal advice — verify every output against current court rules before filing.
- 23 state specialty courts lack public exemplars.

## Using a template

Requires Typst, poppler, jq, just, cargo (or bootstrap script).

```bash
just find ca1                          # locate court + doc types
just new ca1 opening-brief ./brief.md  # starter Markdown with YAML contract
# edit parties, facts, arguments, cites
just build ca1 opening-brief ./brief.md
# or
just render-filing <folder> ./brief.md ./out.pdf
just overlay <folder>                  # red/blue visual diff vs filed exemplar
```

Look at every page. Each doc-type README lists rules, Markdown contract, and known gaps.

## Automation / agents

Highly automatable for mechanical parts:

- Template selection, Markdown drafting, PDF render, overlay comparison, contribution of new templates.
- Explicit agent skills in the repo: `skills/formbook/` (use/render) and `skills/formbook-review/` (review walkthrough).
- Contribution loop:

```bash
just contribute pick
just contribute claim <id>
just contribute brief <id>
# work inside claimed folder
just contribute verify <id>
just contribute submit <id>
```

Final “safe to file” judgment is **not** automatable — requires licensed attorney review against current rules. Nothing is marked done.

## Quality caveats

- Machine-checked ≠ human-verified.
- Rules change; always re-check.
- DOCX may not match Typst for complex layouts.
- Low external traction so far; very new.

## Sources

- https://github.com/davidawad/formbook
- Author post on agent-scale construction: https://davidaw.ad/posts/formbook-at-scale/
