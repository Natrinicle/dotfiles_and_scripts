---
name: decision-judge
description: >
  Use when the user asks which course of action to take, which option or tool
  to pick, whether to do X, A vs B vs C, or an open "what should I do about X"
  with real tradeoffs — including when they say "just tell me" or picking
  in-session seems faster. Also /decision-judge, "run the court", "steelman
  both sides". Do not use for interpersonal conflict or friction with a person
  (use adversarial-analysis), post-hoc verification (check-work), or when there
  is no real tradeoff.
---

# Decision Judge

Parent session is the judge. Spawn advocates. Do not argue both sides in-session, do not pre-pick, and do not spawn a second judge.

**Violating the letter is violating the spirit.** "Just tell me" / "don't stall" is not a skip.

## When not to use

- No real tradeoff — just do the work (lint one-liners, missing `name:`, typo)
- User already decided
- Pure factual lookup
- Interpersonal **conflict** (friction, relationship pattern, source material about people in conflict) → **stop** and use **adversarial-analysis**. Do not run this court on top. A logistics choice that happens to involve a person stays here.
- After-the-fact verify → **check-work**

## Flow

1. Normalize into one framed question + labeled options. If you cannot frame options, ask — do not spawn.
2. Handoff check (above).
3. Panel size from the table. State the matching row in one line. If unsure, **vibe conflicts**, or **two rows disagree**, ask — do not silently override.
4. Same evidence pack to every advocate. Read-only children. They argue; they do not implement.
5. Spawn 2 or 4 `general-purpose` advocates **in parallel** (one parent message). Grok: `spawn_subagent`, `capability_mode: read-only`, description prefix `[for-best]` (etc.). Claude: parallel Agent. No `persona` parameter. Do not pin to local 8B.
6. **No recommendation until advocate results are in.** If spawn is blocked (nested depth), output normalize + panel + pack + planned roles, `recommendation: deferred`, and stop. Do not substitute an in-session pick.
7. Verdict. Then continue-rule.

## Panel size

| Situation | Panel |
|-----------|-------|
| Yes/no or do/don't; well understood; reversible; low blast radius | **2** |
| 3+ live options | **4** (mapping below) |
| Software / tool / vendor / library A vs B | **4** |
| Hard to reverse, expensive, or a long-lived default | **4** |
| Architecture / platform / "which stack" | **4** |
| Interpersonal conflict + source material | **Hand off** adversarial-analysis |
| Involves a person, not a conflict | Stay; **2** unless another 4-row matches |
| Open problem, no options yet | Frame options, **then** re-apply this table |
| Unsure, vibe ≠ table, or two rows disagree | **Ask** |

**2 roles:** `[for-best]` steelman A / the motion. `[against-best]` steelman don't / B.

**4 roles (A vs B):** `[for-best]` `[for-worst]` `[against-best]` `[against-worst]`.

**3+ live options:** one `[option-N-best]` per leading option (cap 3) plus one `[shared-worst]` (failure modes across them). Dropped options stay in the brief as fallbacks. Do not fake a binary court.

**Worst-arguments:** weak reasons people still pick this side, and how the case fails. Not a parody.

## Evidence pack (identical)

Framed question; option labels; this child's role; constraints and non-goals; known facts vs unknowns; binding local-first (no commit / push / PR comment / server or cluster mutate without an explicit ask); output schema; do not invent facts — list gaps.

### Advocate output

claim, 3–7 arguments, key risks, what would change their mind, gaps. No implementation.

## Verdict

- Framed question
- Panel used and why (table row + vibe, or "asked because…")
- Recommendation (one course, or an explicit hybrid that steals a real constraint)
- Confidence
- Why (cite advocates)
- Dissent / kill-criteria
- **Next:** first implementation step, **or** wait: "Say go to implement, or pick another option"

Degraded: retry a dead advocate once, then judge on what returned and mark **degraded**.

## Continue rule

Implement only if this turn (or a still-in-force instruction) already asked to do the work after deciding. Bare "which should I use?" waits.

Continue unlocks **starting** the work. It does not unlock landing actions (commit, push, PR comment, server/cluster mutate). Those still need an explicit ask.

## Routing

Task ids: `decision-normalize` (parent), `decision-advocate` (T3, inherit parent / `general-purpose`). Never ollama/gemma4 for advocates.

## Red flags

| Excuse | Reality |
|--------|---------|
| "I'll just argue both sides here" | Spawn. In-session court is the failure. |
| "Just tell me" / "don't stall" | Still court when the table says court. |
| "I already know the answer" | That is a vibe. Run the table. Conflict → ask. |
| "Can't spawn nested, so I'll pick" | Emit the spawn plan; `recommendation: deferred`. Parent spawns. |
| "Interpersonal, I'll do 4 advocates" | Hand off adversarial-analysis. |
| "They said continue / keep going" | Not implement permission unless the work was already requested. |
| "Continue means helm apply" | No. Landing actions still need an explicit ask. |
| "I'll pick and they can disagree" | Spawn first. Wait is not a substitute for advocates. |

## Common mistakes

- Spawning a judge child
- Different briefs per advocate
- Advocates with write/mutate
- Recommending before results
- Four-quadrant labels on 3+ true options
- Courting a no-tradeoff lint fix
