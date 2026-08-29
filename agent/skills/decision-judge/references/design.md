# Decision Judge — design (2026-08-28)

Accepted in session. `SKILL.md` is the source of truth for the workflow.

## Goal

Parent session acts as judge: normalize any decision input, hand interpersonal **conflict** to `adversarial-analysis`, pick a 2- or 4-advocate panel from a table (ask if unsure or vibe conflicts), spawn read-only advocates, verdict, then wait unless the user already asked to do the work.

## Non-goals

- Replace `adversarial-analysis` (people-court) or `check-work` (after-the-fact verify).
- Spawn a second judge.
- Pin advocates to local 8B models.
- Unlock commit/push/cluster mutate via the continue rule.

## Files

- `{AGENT_HOME}/skills/decision-judge/SKILL.md`
- `{AGENT_HOME}/skills/decision-judge/references/design.md` (this file)
- Grok: symlink `{GROK_HOME}/skills/decision-judge` → Claude copy
- Toolkit: `agent/skills/decision-judge/` in `dotfiles_and_scripts`

## Routing

| Task ID | Owner | Tier |
|---------|-------|------|
| `decision-normalize` | parent | T3 (in-session) |
| `decision-advocate` | `general-purpose`, inherit parent | T3 |

## Tests

Workspace: `~/tmp/decision-judge-workspace/`. RED (no skill) then GREEN (with skill) on: Compose vs k3s (4, wait), interpersonal conflict (handoff), Ansible `name:` (skip court), Kind/Traefik (court then continue local plan only).
