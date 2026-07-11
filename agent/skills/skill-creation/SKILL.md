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

Frontmatter (`name`, `description`), overview, decision rules, anti-patterns unique
to this environment, references. Register discoverability where the host expects it.
