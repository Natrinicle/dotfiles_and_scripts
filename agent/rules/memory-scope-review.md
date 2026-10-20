# Where to Store Agent Knowledge

Before writing a lasting note (memory, rule, skill, hook):

## 1. Scope
- **Global** if it helps in any repo (preferences, machine setup, agent behavior)
- **Project** if it only matters for one codebase or team

## 2. Size
- Short universal prefs → always-on index / rules
- Durable as-builts → MemPalace (one source; trigger is `kg_query` + search)
- Long harness SOPs / unfiled notes → lazy-load files with a one-line trigger

## 3. Discoverability
Lazy-loaded facts need a trigger so agents know when to query the palace
or open a remaining disk file. Empty palace: widen once, then a listed
disk fallback if it exists; do not invent.

Prefer skills for workflows that should load on demand rather than every session.
