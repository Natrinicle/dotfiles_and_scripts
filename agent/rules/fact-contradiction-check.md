---
paths:
  - "**"
---

# Check for fact contradictions on write

Before filing a new Fact about a Person or Company, search MemPalace for
existing Facts on the same entity. Flag contradictions or material updates
instead of silently overwriting.

## Trigger

Any `kg_add` or mine that creates or updates a Fact node.

## Required actions

1. `kg_query` / search for prior Facts linked to the same Person or Company.
2. If a conflict exists (different number, date, commitment, or preference):
   - Keep both with timestamps and source citations.
   - Surface the contradiction in the reply.
3. If it is a clear update (newer source supersedes), use `kg_supersede` and note the change.
4. Never drop the older Fact without recording the supersede.

## Related

- Skill `entity-extract`
- Rule `prefer-mempalace`
- Skill `person-timeline`
