---
paths:
  - "**"
---

# Expected value

Take an expensive action only when it has an edge. Formula and ledger: skill
`expected-value`.

```text
EV = p · b − (1 − p)
```

Take only when EV > 0. Ledger rows: USD, tokens, wall-clock,
**context-window**, **parent compaction**, user wait, spawn budget, blast
radius. Binding resource = scarcest this turn. USD is one row.

## Spawn (context-window is a value)

On every subagent spawn, score parent context:

- Payoff: parent tokens avoided (`C_parent_do`) **plus** avoided parent
  compaction (`C_compact_parent`: window-in + summary-out at parent $/token)
- Stake: brief + re-ingest (`C_prompt + C_reingest`)
- Child fill and spawn-type tax (`C_inject`) drop `p` if the child overflows
- Parallel `N`: `Σ C_reingest` must fit a fraction of remaining parent
  context (`C_rem`). Leave headroom for the answer.
- Cheap/local child's own compact is `$0`. Prefer that hedge when parent-do
  would grow the expensive window. Hedge holds when `C_reingest` stays small.

Unknown-path search / large extract / decompile: spawn (context payoff is
the point). T0 text already in context: direct local generate. Extra cloud
children need their own edge. Cap `N` so the parent can still answer.

## Cheap vs expensive

Skip the spreadsheet: palace query, named file, one grep, direct local
generate, default local explore for unknown paths.

Run the 4-number check (`p`, stake, payoff, binding resource) before cloud
spawn, extra children, browser, crawl, REA, full suite, image/video, or
large parent ingest.

User-named actions are already bets; still size context. Hard gates
(`ask-before-remote-actions`, `public-api-auth`, `independent-checker`,
`pre-commit-gate`, `system-security`) are not EV-skippable. Estimating EV
must cost less than the action.

Compaction **cost** is `C_compact_parent`. Compaction **durability**
(file necessary pieces to MemPalace so later lookup is full drawers):
rule `mempalace-compact-filing`. The compact summary is not filing.
