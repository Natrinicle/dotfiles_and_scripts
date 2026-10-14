# MemPalace timeline — current truth vs history

Facts change. **Keep older drawers.** Current truth is the newest KG fact, then the newest `filed_at`.

When a single-valued fact or preference **replaces** an earlier value:

1. `mempalace_kg_query` on the entity (no `as_of` = now)
2. `mempalace_kg_supersede` — that **expires** the old triple (`valid_to`) and installs the new one. Do not stack two current values. Leave older drawers in place.
3. Mine a dated note: `as_of:`, `status: current`, `SUPERSEDES:`

When search hits conflict: current KG, then higher `filed_at` / `source_mtime`, then `SUPERSEDES:` / `status: current` in the text.

Hybrid search does not rank by age. Point-in-time: `mempalace_kg_query(..., as_of=YYYY-MM-DD)`. Full SOP: `{MEMORY_ROOT}/mempalace-recency-and-preferences.md`.
