---
name: mempalace-scope
description: Use when deciding which MemPalace targets (local, a company palace) a read or write should reach; when a write lands in the wrong palace; when the router reports queued, partial, refused or corrections; or when replicating a fact to a company palace.
---

# MemPalace scope

The router (default HTTP port `8770`) sits in front of the `local` palace and
zero or more company palaces. You choose targets per call; the router
enforces them. Policy summary: rule `mempalace-scope`.

## The `scope` argument

Every `mempalace_*` tool accepts `scope`:

```json
{"scope": ["local", "<company>"]}
```

- `local` is added automatically if omitted. Company-only scope does not exist.
- Two companies in one call returns an error. Use `router_replicate` instead.
- Reads default to `local`; add a company to read its palace too.

## Classify by content

| Situation | Scope |
|---|---|
| Cluster runbook, repo architecture, internal API shape, ticket decision | `["local", "<company>"]` |
| sysctl tweak on the laptop, IR remote decode, BLE device protocol, home router | `["local"]` |
| Session mixes a cluster fix and a personal GPU note | Two writes: one `["local", "<company>"]`, one `["local"]` |
| Might be work, might be personal | Ask (below); no company write until answered |

Ambiguous question template:

> This looks like it could belong to <company>'s palace (signal: …). File to <company> + local, or local only?

Working directory, an employer parent model, and user hints are signals for
the classification. They do not decide it.

## Router tools

- `router_targets`: configured targets and `todo` (pending outbox pushes).
- `router_status`: router health, ledger size and the same `todo`.
- `router_mine(dir, scope, wing?, room?)`: mine a directory into the scope.
- `router_flush(target)`: push that target's queued outbox now.
- `router_retract(ref, target=None)`: remove a filed item from a company palace,
  and drop it from the outbox if it is still queued (`dequeued`). The local copy stays.
- `router_replicate(ref_or_fact, to=[...])`: copy to company palaces; the only multi-company path.

## Response fields

| Field | Meaning | Say |
|---|---|---|
| `filed_to` | Targets that accepted the write | Name them |
| `tag: "filed → <company> + local"` | Router's own summary | Echo verbatim |
| `queued_for` | Company unreachable; item in outbox | "Saved locally, queued for <company>" |
| `partial` | Some targets accepted, some did not | List which; offer `router_flush` |
| `refused` | Router blocked it, e.g. `secret_pattern:<name>` (writes, and reads whose query looks like a secret) | Say why; remove the secret; do not retry blindly |
| `corrections` (on company `kg_query`) | Corrections in both directions: the older side's fact was superseded with the newer, for allowlisted single-valued predicates only (`version`, `interface_kind`, `reach`, `status` by default) | Surface them; prefer the corrected value |
| `fallback: "added (no prior fact)"` | Company lacked the old triple, so the supersede became a `kg_add` there | Say so |

Unknown tools route local-only and return a note; relay it.

## Wrong palace: retract

1. User says "that shouldn't be in <company>".
2. `router_retract(ref, target="<company>")` (omit `target` only when unambiguous).
3. Search-verify the company scope no longer returns it.

Retracting a ledgered `kg_supersede` invalidates the new object on the
company palace. It does not restore the old object; re-add it if needed.
4. Id-bound tools (`get_drawer`, `delete_drawer`, `update_drawer`, ...) refuse
   company scope. Use `router_retract`, not `delete_drawer`.

## Replicate

User asks to also file something to another company: `router_replicate(ref_or_fact, to=["<company>"])`.
Check classification and secrets first. Echo the returned `tag`.

## Outbox

If `router_targets.todo` is non-empty, tell the user which targets have
pending pushes and offer `router_flush(target)`. Do not flush unasked.

## Taxonomy

The router maps wing and room names per target. Pass the names you would use
locally; never rename to fit a company palace.

## Do not

- Use a company-only scope (omit `local`).
- Put two companies in one `scope`.
- Send secrets, tokens, or personal-account material to a company palace.
- File a company write while the classification is unclear.
- Paraphrase `tag`; echo it.
- Call `delete_drawer` on a company-scoped item.
