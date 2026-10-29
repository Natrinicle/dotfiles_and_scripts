---
name: entity-extract
description: >
  Extract and link Person, Company, Fact, Memory, Note, File, and Meeting
  entities from emails, calendar events, posts, files, or notes into MemPalace.
  Use when ingesting any source material that mentions people, companies,
  decisions, or facts, or when the user asks to extract entities, build the
  personal graph, or link new information to You.
---

# Entity Extract

Turn raw source material into linked nodes in the You-centered graph
(Person, Company, Fact, Memory/Note, File, Meeting, Email, Post).

Prefer MemPalace (`kg_add` / `kg_supersede` + mine). Solid edge = explicit
mention; dashed = co-occurrence or context inference.

## When to run

- New or updated email, meeting, post, file, or note arrives
- User asks to extract entities, update the graph, or link something to a person/company
- After scanners (inbox, Slack, Jira, Speakr, etc.) produce new material

## Workflow

1. Identify source type (Email / Meeting / Post / File / Note).
2. Extract:
   - People (names, emails, roles) → Person nodes
   - Organizations (companies, teams, domains) → Company nodes
   - Explicit decisions, numbers, preferences, commitments → Fact nodes
   - Action items or free-form context → Note / Memory drawers
3. Link each extracted entity to the source and to You. Record solid vs dashed.
4. `kg_add` (or `kg_supersede` on clear update). Stage a directory and
   `mempalace mine DIR --daemon` the same turn. Search-verify the source filename.
5. Hand any new or changed Person to `contact-syncer` / `update-contacts-from-sources`.

## Edge rules

- Solid: name/email/title appears in the source.
- Dashed: co-mentioned, inferred from domain, or context-only.
- Never invent a Person or Company that is not grounded in the source.

## Related

- Rule `entity-extract-on-ingest` (always-on trigger)
- Rule `prefer-mempalace`
- Skills `contact-syncer`, `mempalace`, `meeting-to-graph`, `person-timeline`
