---
name: skill-creation
description: Write lean skills with strong triggers and only non-obvious project knowledge.
---

# Skill Creation

## Skill vs command

- **Skill:** knowledge + decision rules, auto-loaded by description  
- **Command:** explicit multi-step user invocation  

## Efficiency

- Omit training-data platitudes  
- Prefer pointers to exemplar files over huge templates  
- Target ~100–200 lines; split if larger  
- Descriptions must include when-to-use phrases  

## Structure

Required frontmatter is `name` and `description` (include trigger phrases).
`applies-to` is optional. Overview, decision rules, environment-specific
anti-patterns, references. Do not register skills in `packages/ide/AGENTS.md`;
discoverability is the description. Follow bundled `skill-design-principles`
when the host provides it.
