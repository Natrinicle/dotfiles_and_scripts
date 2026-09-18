# Pandoc Templates Examples

This directory contains example Markdown files that demonstrate useful Pandoc + XeLaTeX document layouts, along with their rendered PDF counterparts.

These examples are designed to work with the `md2pdf` helper defined in `shell/bash_aliases.d/documents`.

## md2pdf Helper

`md2pdf` is a thin convenience wrapper around Pandoc that converts a Markdown file to PDF using the XeLaTeX engine:

```bash
md2pdf <file.md>
```

`resume.md` here uses the same XeLaTeX header as `agent/skills/resume-tailor`. Fill `references/facts.md` from that skill's `facts.example.md` before tailoring a real resume. The helper needs `pandoc` and XeLaTeX on PATH.
