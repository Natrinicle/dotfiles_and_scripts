---
name: update-contacts-from-sources
description: >
  Create and patch address-book cards from Gmail, Voice, vCards, and other
  identity data. Use when updating contacts, merging extra emails or phones,
  creating missing people or businesses, or cleaning "Me to" / "Voicemail from"
  cruft. Some cards are organizations. Distinct from contact-syncer
  (IM/profile/macOS).
---

# Update contacts from available information

Create or patch **address-book cards** from dumps and live sources. Some cards
are **businesses**. Call-log titles are **cruft**, not names.

Use **contact-syncer** for IM/profile notes, friction, and commitments.

## When to run

- Update contacts from Gmail, Voice takeout, vCard dumps, or extra-field JSON
- Create missing people **or** organizations
- Patch extra emails, phones, org, title, or photo onto an existing card
- User says a card is a clinic, firm, school, or store rather than a person
- FN looks like `Me to …` or `Voicemail from …`

## Classify every candidate

| Class | Treat as | Typical signals |
|-------|----------|-----------------|
| Person | Human card | Given + family name; a staff mailbox |
| Organization | Business card | Clinic, firm, school, store as FN; main phone; no personal mailbox |
| Cruft | Skip as identity | Call-log / Voice auto-titles (below) |
| Skip | Do not CREATE or merge | On-call dumps, generic retailer names, FN-only junk |

### Organizations

A business is a valid contact. Keep it as the org (name, main phone, website).

A person who **works at** that business is a **separate** card with an
organization field. Do not put a staff member's email or nickname on the org
card. Other staff at the same org stay as their own people.

### Cruft (not a name)

Case-insensitive FN prefixes that are call-log titles:

- `Me to `, `Me-to `
- `Voicemail from `, `Voice mail from `
- `Missed call from `, `Call from `

Do not CREATE a card whose only FN is that title. Do not merge that FN onto a
real person unless the user confirms. Do not re-import a Voice CSV of those
rows.

## Match conservatively

1. Email (case-insensitive)
2. Phone (digits only, ≥10)
3. Exact display name (one unique hit)

Then:

- Extra emails and phones **append** to existing arrays
- Prefer the **longer** name when it is a superset of the shorter one
- Skip FN swaps that are not a superset
- Skip cards with many rotating phones (paging / on-call)
- Skip a source with no unique match in the live book

## Write policy

- Propose CREATE / PATCH / SKIP unless the user already asked to write
- Do not re-import a full unique dump into a live book
- Do not dump into vendor caches (for example KDE Connect `kpeoplevcard`)
- CREATE-only CSV imports do not merge extras; extras need a patch API
- Do not steal browser cookies for directory APIs; use the host's existing
  account tokens
- Ask before git commit or push of helper scripts

## Process

1. Inventory live books vs source dumps.
2. Classify each candidate (person / organization / cruft / skip).
3. Match to existing cards.
4. Propose CREATE vs PATCH vs SKIP with the match key.
5. Write only after the user asked, or they already said create/patch.
6. Re-list the live book and confirm person vs org stayed split.
7. Update the host contacts runbook if one exists.

## Vendor notes

- **Google People:** `updateContact` replaces listed fields. To clear a field,
  omit it in the body and name it in `updatePersonFields`. GET `personFields`
  must not include `etag` (etag still returns on the resource).
- **KDE Akonadi:** local Personal Contacts and a Google Groupware resource are
  different collections. Sync the resource after People API writes.
- **macOS Contacts:** `contact-syncer` owns osascript. This skill still
  classifies person vs org vs cruft for that path.
