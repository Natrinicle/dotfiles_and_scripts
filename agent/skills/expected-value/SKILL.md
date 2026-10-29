---
name: expected-value
description: >
  Use when choosing whether to spend money, tokens, wall-clock, or context;
  before spawning a subagent; when parent compaction is likely; when a
  cheap or local child might beat parent-do; when an action looks expensive;
  "is this worth it", "+EV", "skip this bet", expected value, Kelly,
  bankroll, context-window or compaction cost of a spawn.
---

# Expected Value

Take an action only when it has an edge. Unit-stake formula (racing / Benter):

```text
EV = p · b − (1 − p)
```

- `p` — probability the action produces the needed result
- `b` — net payoff per unit stake if it works (same unit as the stake)
- `s` — stake: what the try costs

Take the action only when EV > 0, i.e. `p > 1/(b+1)`. Scale by stake:
`total EV = s · (p·b − (1−p))`.

Absolute form: `EV = p·benefit − (1−p)·loss − sure_cost`.

## Ledger

Score the same action on each row. Binding resource = the scarcest this turn.

| Resource | Stake | Payoff if it works |
|----------|-------|--------------------|
| USD | API / cloud spend | Dollars avoided later, or value of the result |
| Tokens | Input + output billed | Tokens not spent on a worse path |
| Wall-clock | Seconds until the result | Time saved vs the alternative |
| Context-window | Parent fill + child fill + re-ingest | Parent tokens not spent in-session |
| Parent compaction | Next compact: window-in + summary-out at **parent** $/token | Avoided parent compact; child compact is the child's rate ($0 local) |
| User wait | Session blocked | Unblocked progress |
| Spawn budget | One child slot | A finished slice |
| Blast radius | Chance of a harmful wrong answer | Avoided damage |

USD is one row. A free local spawn can still be −EV on context-window or wall-clock. Compaction is its own row: the parent bills **oodles in and out** on the expensive model.

## Context-window is a spawn value

On every `spawn_subagent` / Agent child, context-window is a first-class
line, often the binding one. The value of spawning is parent context
preserved.

| Term | Meaning |
|------|---------|
| `C_rem` | Remaining parent context (bankroll) |
| `C_parent_do` | Tokens the parent would spend doing the work in-session |
| `C_prompt` | Brief sent to the child |
| `C_inject` | Child-side spawn tax (explore / system prompt). Direct Ollama for T0 text skips this |
| `C_child_fill` | Expected child window use (brief + tools + output). Overflow drops `p` |
| `C_reingest` | Parent tokens to read the child report |
| `N` | Parallel children; parent pays `Σ C_reingest` |
| `C_compact_parent` | Next parent compact: current window as **input** + summary as **output**, at parent $/token |
| `C_compact_child` | Same shape at the **child** rate (`$0` if local) |

Parent-window EV of a spawn (tokens):

- Stake ≈ `C_prompt + C_reingest`
- Benefit if it works ≈ `C_parent_do` **plus** avoided `C_compact_parent`
- Take the spawn when `p · (C_parent_do + avoided C_compact_parent) > C_prompt + C_reingest`
- Size: `Σ C_reingest` fits a **fraction** of `C_rem`. Leave headroom for the user-facing answer.
- Hedge holds when `C_reingest` stays small vs that payoff. A cloud child that dumps a novel is a weak hedge.

Parent-do grows the expensive window. That raises both **P(compact)** and
`C_compact_parent`. A cheap or local child does the slice (and any child-window
compact) off the parent. Which child model: `model-router` cheapest viable
tier; local is the strongest compact hedge. Escalate once if the cheap child
is empty or shallow.

Low `C_rem` makes a scoped child high value (protects the bankroll).
Unknown-path search, large-file extract, decompile: `C_parent_do` is large →
spawn (agrees with `subagents-first`).
T0 text already in context: `C_inject` of explore is large → direct generate
(`skill-router`).
`N` parallel cloud children: each may be +EV alone; the book is −EV when
`Σ C_reingest` blows `C_rem`.

Child window is its own bankroll. A huge brief into a small local child
lowers `p`. Shrink the brief (`local-brief`) or pick a bigger window.

## When to run the numbers

Cached +EV (no spreadsheet): palace query, named-file read, one grep,
direct local generate, the default local `explore` / `code-explorer` for
unknown-path search.

Run the 4-number check (`p`, `s`, `b`, binding resource) before:

- Cloud `general-purpose` / reviewer / advocate spawn
- Extra or overlapping children
- Browser, crawl, REA decompile, full test suite, image/video
- Ingesting a large file into the parent
- Re-reading a long skill or routing table

Estimating EV must cost less than the action.

## Skip, size, or take

1. User named the action → take it (they already bet). Still size context
   (scoped child, `local-brief`, cap `N`).
2. Binding EV ≤ 0 → take the cheaper alternative, or ask. Do not silently
   drop the request.
3. Binding EV > 0 → take it; stake a fraction of the bankroll (Kelly).
4. Hard gates still apply: `ask-before-remote-actions`, `public-api-auth`,
   `independent-checker`, `pre-commit-gate`, `employer-pr-findings-gate`,
   `system-security`. EV does not waive those.

Which model: `model-router` / `skill-router`. Whether to spend at all: this
skill.

## Worked calls

| Situation | Binding | Call |
|-----------|---------|------|
| Palace already has the GATT map | tokens + time | Skip re-decompile |
| Unknown-path “where is X” | context-window | Local explore (`C_parent_do` ≫ `C_reingest`) |
| Parent context 80% full, large extract | context-window + compact | Spawn scoped cheap/local child |
| Four cloud advocates for a typo | USD + time | Skip court (`decision-judge` no-tradeoff) |
| User said run the full suite | named bet | Run it |
| T0 extract already in context | tokens + `C_inject` | Direct Ollama, no explore |
| Eight parallel cloud reports | context-window | Cut `N` so `Σ C_reingest` fits `C_rem` |
| 8 min cloud child vs 5 s local check | wall-clock | Local first, escalate once |

## Rationalizations

| Excuse | Reality |
|--------|---------|
| “It's only tokens, not money” | Tokens, context-window, and parent compaction are ledger rows |
| “Spawn is free on local” | Child fill + re-ingest + wait are not free; local compact is |
| “Context is already here, I'll grep” | Parent-do grows the expensive window; next compact is in+out at parent rate; spawn a cheap/local child |
| “Compaction is automatic, keep it on the parent” | Compaction is a billed parent pass (`C_compact_parent`) |
| “Spawn a cloud T3 child to save compact” | Child work is still billed; the hedge is cheap/local plus small `C_reingest` |
| “One more child just in case” | Extra child needs its own edge |
| “I'll read the whole routing table” | Cached pin; re-read is −EV |
| “EV takes too long to compute” | Cheap actions skip the ledger |
| “Positive EV, dump the window” | Size the stake; leave answer headroom |

## Related

- `model-routing` / `model-router` / `skill-router` — which model (cheapest viable child; local is the compact hedge)
- `subagents-first` — child-capable work goes to a child; this skill scores that spawn's context-window and parent compaction
- `mempalace-compact-filing` — durability hedge: file necessary pieces to MemPalace before compact so later `C_reingest` is a palace lookup. This skill scores the compact **cost** (`C_compact_parent`); that rule owns filing.
- `decision-judge` — user-facing A vs B court (skip when no tradeoff)
