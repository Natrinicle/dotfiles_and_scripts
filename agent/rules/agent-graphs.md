---
paths:
  - "**"
---

# Agent graphs

A prompt is one message. A **loop** makes one unit correct. A **graph**
decides which units exist, which run together, and where results go back.

Layers stack. They do not replace each other: prompt → context → harness
→ loop → graph. Procedure: skill `agent-graphs`. Inner retry: skill
`loop-until-green`.

## Shape

- An **edge** exists only when the next step **reads** a named output from
  the previous one. "And then" is not an edge.
- **Nodes:** splitter, worker, code, gate. If the transform needs no
  judge / decide / assess / summarize, it is a **code** node.
- Workers get **one unit, one lens, their own context**. Shared windows
  echo the first opinion.
- The loop lives **inside** a node. The graph lives **between** nodes.

## Gate and return

Write a programmable check first. "Looks good", "the model is confident",
and "no errors were raised" are not checks.

Return the **unit**, not the batch: unit, verdict, reason, evidence, scope.
Cap a unit at three corrections; then the plan is wrong.

Open a lane on **blast radius** (how expensive a wrong change is to undo),
not on confidence. Hard-to-reverse work does not open.

Put the human on **one** step: highest consequence, lowest reversibility.
Landing still follows **ask-before-remote-actions**.

A verdict that does not change what runs next is a report. A failure that
does not become a splitter constraint will recur.

Bug hunt stays **find-patch-loop**. Session-complete stays **check-work**.
Spawn cost stays **expected-value**. Checker ≠ producer stays
**independent-checker**.
