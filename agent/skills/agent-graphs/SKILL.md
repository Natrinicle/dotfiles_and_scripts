---
name: agent-graphs
description: >
  Use when work is a line of and-then steps, a swarm, a self-improving
  agent system, graph engineering, splitter worker gate, fake
  dependencies, or deciding which units exist and run in parallel.
---

# Agent graphs

Dispatcher for the **shape** of multi-agent work. A loop makes one unit
correct. A graph decides which units exist.

**REQUIRED SUB-SKILL:** **loop-until-green** for produce / check / correct
inside a node.
**REQUIRED:** **expected-value** on every spawn.
**REQUIRED:** **subagents-first** for child-capable units.
**REQUIRED:** **independent-checker** on every gate.

Bug hunt is **find-patch-loop**. Session-complete is **check-work**.
Landing is **ask-before-remote-actions**.

## When this layer pays

This layer is the better shape when several units do not consume each
other's output, or a gate / named output sits between steps. One unit
→ `spawn_subagent` (rule **subagents-first**). Parent-wide grep / list /
`rg` is **denied** by hook `prefer-spawn-search`. Do not search the tree
on the parent “for context”.

Use a graph when any of these is true:

- Two steps do not consume each other's output
- Several units can run at once
- The human is reviewing intermediate steps
- The same class of failure comes back next run

Stay on one loop (no graph) when one context can hold the whole job and
every later step reads the previous output.

## Draw, then cut

1. Name the **splitter** dimension (blast radius, file, claim, slice).
   The wrong cut duplicates work or hides it.
2. List nodes. Vocabulary is only: splitter, worker, code, gate.
3. For every arrow: name the **variable that crosses**. If none, delete
   the arrow and fan out.
4. Put a **programmable check** on every worker (skill `loop-until-green`).
5. Place **one** human gate at highest consequence, lowest reversibility.
6. Add two back edges: **correction** (this run, one unit) and
   **learning** (a constraint into the splitter's next brief).

Grok Build: optional workflow `agent-graph` (split → isolated workers →
independent gate). It does not land commits.

## Node jobs

| Node | Job | Must not |
|------|-----|----------|
| Splitter | Cut units; apply learned constraints | Do the units |
| Worker | One unit, one lens, own context | Grade itself; read sibling drafts |
| Code | Merge, rank, dedup, diff, count | Call a model |
| Gate | Run the check; return or accept | Use confidence as the variable |

A graph where every edge is an agent pays rent on its own wiring.

## Return paths

**Correction (short):** gate sends **one** red unit back.

```text
UNIT      handlers slice
VERDICT   red
REASON    test_auth_redirect failed
EVIDENCE  expected 302, got 200, handlers/auth.py:88
SCOPE     this file only
```

**Learning (long):** an accepted result becomes a **constraint** on the
splitter, not extra text on the worker. File it (MemPalace / rule) so the
next run starts where this one ended.

## Lanes (blast radius)

| Lane | Example | Open? |
|------|---------|-------|
| Reversible, contained | Copy, test, isolated function with coverage | Yes, after the check |
| Reversible, wide | Shared util, schema, many callers | Deterministic checks + clean trajectory |
| Hard to reverse | Migration, deletion, prod data, money | Closed. Human named the landing. |

Inside an open lane, read evidence in order: deterministic result, this
run's trajectory, prior rollbacks from this node, model self-score last.

## Build order

1. Gate (something can fail loudly)
2. Lanes
3. Learning edge last

## Rationalizations

| Excuse | Reality |
|--------|---------|
| "I'll keep it as one agent and prompt harder" | The fault is the shape, not the message |
| "Four workers can share a window" | They echo the first finding |
| "The merge needs judgment" | Rank / dedup / diff is a code node |
| "Send the whole batch back" | Correct units get rewritten; it diverges |
| "Confidence is 0.9, ship it" | Confidence is the input the model can move |
| "Human reviews every step" | The human is the slowest node |
| "The verdict is in the log" | If it does not change what runs next, it is a report |

## Do not

- Treat "and then" as a dependency
- Grow **find-patch-loop** or **check-work** into this dispatcher
- Spawn extra workers that **expected-value** would skip
- Land commits or server changes unless the user named that step
