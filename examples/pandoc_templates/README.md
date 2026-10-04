# Pandoc Templates Examples

This directory contains example Markdown files that demonstrate useful Pandoc + XeLaTeX document layouts, along with their rendered PDF counterparts.

These examples are designed to work with the `md2pdf` helper defined in `shell/bash_aliases.d/documents`.

## md2pdf / convert_document

`md2pdf` is a convenience wrapper around `convert_document`. It writes a PDF next to the input using XeLaTeX. Input format is taken from magic bytes / MIME, then the filename (Markdown, RST, HTML, Org, and similar).

```bash
md2pdf <file.md>
convert_document notes.rst notes.pdf
convert_document README.md README.docx
```

`resume.md` here uses the same XeLaTeX header as `agent/skills/resume-tailor`. Fill `references/facts.md` from that skill's `facts.example.md` before tailoring a real resume. The helper needs `pandoc` and XeLaTeX on PATH.
