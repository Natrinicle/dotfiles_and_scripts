---
paths:
  - "**"
---

# Extract entities on every ingest

When any Email, Meeting, Post, File, or Note is processed, extract and link
Person, Company, Fact, and Note/Memory nodes into MemPalace before the turn ends.

## Trigger

Any scanner output, pasted source material, calendar event, or user request
that contains people, organizations, decisions, or commitments.

## Required actions

1. Run the extraction logic from skill `entity-extract`.
2. Write solid edges for explicit mentions and dashed edges for inferred links.
3. `kg_add` / `kg_supersede` then mine the same turn. Search-verify.
4. Hand new or changed Person nodes to contact sync.

Do not skip because "it might already be known." Prefer updating the graph.

## Related

- Skill `entity-extract`
- Rule `prefer-mempalace`
- Rule `fact-contradiction-check`
