# Where to Store Agent Knowledge

Before writing a lasting note (memory, rule, skill, hook):

## 1. Scope
- **Global** if it helps in any repo (preferences, machine setup, agent behavior)
- **Project** if it only matters for one codebase or team

## 2. Size
- Short universal prefs → always-on index / rules
- Long references → lazy-load files with a one-line trigger

## 3. Discoverability
Lazy-loaded files need a trigger in a rule or MEMORY index so agents know when to open them.

Prefer skills for workflows that should load on demand rather than every session.
