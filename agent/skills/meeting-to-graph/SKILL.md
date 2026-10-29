---
name: meeting-to-graph
description: >
  Process a calendar event or meeting notes into linked Person, Company,
  Fact, Note, and File nodes in MemPalace. Use after a meeting ends, when
  notes arrive, or when the user asks to capture a meeting into the graph.
---

# Meeting to Graph

Turn a meeting into graph edges.

## When to run

- Meeting just ended or notes were shared
- User pastes meeting notes or asks to capture a calendar event
- Morning summary or calendar scan surfaces a completed meeting

## Workflow

1. Load the calendar event (attendees, title, time, description) and any notes/transcript.
2. Extract attendees → Person nodes (solid edges). Domains/orgs → Company.
3. Pull decisions, commitments, and numbers → Fact nodes.
4. Action items and free notes → Note / Memory drawers linked to the Meeting node.
5. Attach any related Files.
6. File into MemPalace the same turn (`kg_add` + mine). Update contacts for new or changed people.
7. Offer a one-line summary of what was filed.

## Related

- Skill `entity-extract` (shared extraction logic)
- Rule `entity-extract-on-ingest`
- Skills `contact-syncer`, `mempalace`
