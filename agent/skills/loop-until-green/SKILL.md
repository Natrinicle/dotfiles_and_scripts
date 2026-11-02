---
name: loop-until-green
description: >
  Use when a unit of work needs a failing check, produce-check-correct,
  loop until green, babysitting an agent through retries, or a review
  that is another model saying it looks good.
---

# Loop until green

A loop is four parts: produce, check, correct, repeat until green. The
**check** is the whole thing.

Without something that can fail the work while the user is out of the
room, this is a scheduler, not a loop.

Graph topology (which units exist, what runs together) is **agent-graphs**.
This skill is **one unit**.

**REQUIRED:** **independent-checker** — the producer does not grade the
check. Another model saying "looks good" is two optimists agreeing.

## Write the check first

The condition must be evaluable by a program:

| Green | Not a check |
|-------|-------------|
| Test suite exits 0 | The output looks good |
| Every claim carries a source line | The model says it is confident |
| Diff touches only files listed in the plan | No errors were raised |

Absence of an error is not evidence of correctness. A check bolted on
after the work is still a check only if it can fail.

## Cycle

1. Write the green condition (command, schema, file list, source span).
2. Produce the unit.
3. Run the check. Record exit, output, or schema errors.
4. On red: return **this unit** with verdict, reason, evidence, scope.
   Produce again. Do not reopen sibling units.
5. Stop on green, on three reds, or when the user stops.

Three reds means the **plan** that produced the unit is wrong. The loop
cannot see the plan. Escalate to the splitter / parent / user.

Session-complete verification after the units are green is **check-work**.

## Return payload

```text
UNIT      <id>
VERDICT   green | red
REASON    <one line>
EVIDENCE  <command output or path>
SCOPE     <what may change on the next produce>
```

Without SCOPE the next produce grows: adjacent files, extra refactors,
unreviewed diffs.

## Cap and carry

- Cap **three** corrections per unit per run.
- Carry the failing evidence into the next produce. Do not restart from
  a blank brief.
- Do not send a green sibling back because one unit was red.

## Rationalizations

| Excuse | Reality |
|--------|---------|
| "No errors in the log" | That is not a check |
| "I'll review it after I build it" | Write the condition first |
| "The worker can score itself" | Producer does not grade |
| "Looks good to another model" | Two optimists |
| "One more try, no new evidence" | Same brief repeats the same miss |
| "Return the whole batch" | Correct work gets rewritten |

## Do not

- Use confidence, vibe, or empty stderr as green
- Retry past three without changing the plan
- Treat compile-only as the check when tests exist
- Declare the session done from a green loop — that is **check-work**
