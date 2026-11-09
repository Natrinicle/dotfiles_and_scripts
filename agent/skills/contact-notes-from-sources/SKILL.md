---
name: contact-notes-from-sources
description: >
  Append short Voice-dump contact notes and addresses. Use for "went to
  this together" notes without replacing existing biographies.
---

# Contact notes from sources

**REQUIRED:** `update-contacts-from-sources` for classify, match, and card
CREATE/PATCH. This skill owns **append-only** biographies and postal
addresses. `contact-syncer` stays IM/profile/macOS.

## When to run

- Google Voice takeout, call HTML, or vCard dumps
- User wants short helpful notes (first meeting, job, favorite color,
  "went to this together")
- A message contains a street address the card is missing

## Style

One fact per line. Useful later. Not a diary.

**Preferred**

- Met at {place} {date}
- {role} at {org}
- Favorite color: {color}
- Went to {place} together
- Enjoys long walks on the beach

**Skip as notes**

- Dump volume (`GV Takeout Text:N`, `files=`, `msgs=`)
- SSN, medical, OTPs, intimate lines, legal strategy
- Call-log titles (`Me to`, `Voicemail from`) as FN or as a note
- Rewriting an existing biography line
- Auto-scraping every “enjoys …” in a thread; write that line by hand

## Append policy

1. Classify and match with `update-contacts-from-sources` (email, then
   10-digit phone, then one unique FN). Skip cruft and non-unique hits.
2. GET the live card first.
3. Keep every existing biography line. Insert a candidate only when it
   is absent (case-insensitive) and is one restrained fact. Put new
   lines **above** a dump-volume footer (`GV Takeout …`) when one exists.
4. Put streets on the **address** field when the card has none. Do not
   also paste the street into the biography unless the user asked.
5. Cap three new note lines per card per run.

Google People: `updateContact` replaces listed fields. GET `biographies`
and `addresses`, concatenate, PATCH those fields. GET `personFields` must
not include `etag`.

## Sources

1. CSV / JSON / vCard first (name, phone). Ignore a Notes column that is
   only dump volume.
2. Call HTML only when a unique match still needs an address or a
   restrained fact.
3. Do not load tens of thousands of HTML files into the parent. Run
   `scripts/extract_contact_notes.py` and read the JSON summary.

```bash
python3 scripts/extract_contact_notes.py --voice-dir "$VOICE" --out /tmp/contact-notes.json
```

## Write

Propose CREATE / PATCH / SKIP unless the user already asked to write.
After People writes, synchronize the Akonadi Google Groupware resource.
Append a Profile Change Log row. `kg_add` Person/org facts; do not file
SSN or medical text.

## Related

- `update-contacts-from-sources` — classify / match / CREATE
- `contact-syncer` — IM/profile/macOS
- `entity-extract` — palace graph
