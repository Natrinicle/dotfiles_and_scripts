---
paths:
  - "**"
---

# MemPalace scope — which palaces a call reaches

The MemPalace router (default `:8770`) fronts `local` plus company palaces.
Every `mempalace_*` call takes `scope: ["local", "<company>"]`; `local` is
added if omitted, and two companies in one call is an error. Pick targets by
**content**, not by habit.

| Content | Scope |
|---|---|
| Company repos, clusters, APIs, tickets, colleagues, internal decisions | `["local", "<company>"]` |
| Personal machine, home LAN, hardware RE, personal accounts | `["local"]` |
| Mixed | Split into two writes, one per scope |
| Unclear | Ask before any company write; reads may use `local` meanwhile |
| User says "also file to X" | `router_replicate` (the only multi-company path) |

- cwd, employer parent model, and hints are inputs, not the decision.
- When a response has `tag` (`filed → <company> + local`), echo it verbatim.
- On "that shouldn't be in <company>": `router_retract(ref)`, then search-verify.
- If `router_targets.todo` is non-empty, say so and offer `router_flush(target)`.

Procedure, response fields, examples: skill `mempalace-scope`.
