---
name: person-timeline
description: >
  Build a chronological timeline for a Person or Company across meetings,
  emails, posts, files, notes, and facts. Use when the user asks for a
  timeline, history with someone, or "what have we done with X".
---

# Person Timeline

Unified chronological view for one Person (or Company) across the graph.

## When to run

- User names a person and asks for history, timeline, last interactions, or open items
- Before drafting a message or preparing for a meeting with that person

## Workflow

1. Resolve the Person (or Company) via MemPalace `kg_query` / search.
2. Pull related Meetings, Emails, Posts, Files, Notes, and Facts
   (prefer newest `filed_at` first).
3. Sort chronologically. Group by type if dense.
4. Surface open actions, contradictions (see rule `fact-contradiction-check`),
   and last solid-edge interaction.
5. Return a short timeline + open items. Offer to expand any source.

## Related

- Skills `entity-extract`, `meeting-to-graph`, `mempalace-recall`
- Rule `prefer-mempalace`
