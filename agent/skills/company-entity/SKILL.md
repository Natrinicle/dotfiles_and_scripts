---
name: company-entity
description: >
  Promote companies and organizations to first-class graph nodes. Link them
  from email domains, meeting titles, file paths, and person affiliations.
  Use when a company appears in source material or the user asks to track an org.
---

# Company Entity

Treat Company like Person: a durable node that other entities link to.

## When to run

- Entity extraction finds an organization
- User asks to track a company, client, or org
- Domain, title, or path clearly implies a company

## Workflow

1. Normalize the company name (prefer the canonical form from the source).
2. Create or update the Company node in MemPalace.
3. Link People who work there, Meetings/Emails that mention it, and related Files/Facts.
4. Prefer solid edges for explicit mentions; dashed for domain-only inference.
5. File the same turn.

## Related

- Skill `entity-extract`
- Rule `entity-extract-on-ingest`
