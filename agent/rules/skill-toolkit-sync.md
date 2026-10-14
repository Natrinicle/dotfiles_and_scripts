# Sync skill and rule updates into toolkits

When you **create or edit a skill or a rule**, copy that change into the
**general pack** in the same turn. Specialized packs are domain-only — see
below. Do not ask “update specialized packs too?” after a general-pack copy.

Load **package-toolkit** for layout, sanitization, classify-first, and
`toolkit.yaml` / README freshness. Do not skip the copy because the home
skill already exists.

## Classify first

**package-toolkit** sanitizes **toolkits**. Decide the kind before copying:

| Kind | Destination |
|------|-------------|
| Generic reusable pack (agent skills/rules, shell helpers, Flipper IR, court monitor) | `general_pack` from toolkit-homes.yaml, or a specialized pack when the domain matches |
| Repo-specific product work (compose, ADRs, services, product hostnames) | That application repo. Residual-scan personal tokens. Keep product names. PR in that repo when the project requires it. |

A compose stack or ADR that names `{product}` stays in that product repo.

## Resolve pack paths from host config

Host layouts differ (`agent/skills/` vs `.claude/skills/`, different
checkouts). Read, in order:

1. `{AGENT_HOME}/config/toolkit-homes.yaml`
2. `~/.claude/config/toolkit-homes.yaml`
3. `{MEMORY_ROOT}/toolkit-homes.md`
4. Example: `{AGENT_HOME}/skills/package-toolkit/references/toolkit-homes.example.yaml`

`general_pack` + `skill_dir` / `rule_dir` is the toolkit. If `toolkit.yaml`
sets `paths.agent_skills`, that wins for that pack.

Do **not** create `{HOME}/repos/<name>-toolkit`. Do **not** invent sibling
names. If the YAML is missing, ask.

## What counts as a toolkit repo

Any of:

- `toolkit.yaml` or `TOOLKIT.md` at the repo root
- `agent/skills/` or `agent/rules/` (portable agent pack)
- `.claude/skills/` plus a pack README that documents those skills

## Current repo (only if it is a toolkit)

If the working tree **is** a toolkit (it has `toolkit.yaml` or a documented
`agent/skills/` pack), copy there too. Application product repos are not
toolkits.

1. Find the toolkit skill/rule directory from `toolkit.yaml` paths, else
   `agent/skills/` and `agent/rules/`, else `.claude/skills/` and
   `.claude/rules/`.
2. Copy the updated skill **tree** (`SKILL.md`, `references/`, `scripts/`) or
   the updated `*.md` rule into that directory, same relative name.
3. If `package-toolkit` sanitization applies, strip homes, logins, and
   employer names.
4. If `toolkit.yaml` exists, bump `version` when the public surface changed,
   and keep `agent_skills_included` / `agent_rules_included` accurate.
5. Update the toolkit `README.md` in the same change when install paths,
   counts, or listed skills/rules changed.

Do this even when the edit started in `{AGENT_HOME}/skills` or
`{AGENT_HOME}/rules`. The general pack still gets the copy.

## Specialized packs (domain only)

`remote_codes` and `court-case-monitor-toolkit` only receive artifacts that
belong to that pack. Copy into a specialized pack in the same turn when
**either**:

- The pack already ships that skill or rule (`toolkit.yaml`, README, or the
  skill/rule directory in that repo), or
- The artifact is specific to what that pack publishes (Flipper IR, raw IR
  decode, BLE/GATT, APK/firmware unpack for `remote_codes`; court calendar /
  CaseLook monitoring for `court-case-monitor-toolkit`).

Otherwise copy **only** to `general_pack`. Do **not** ask “update specialized
packs too?”.

Ask only when a **new** domain skill might belong in a specialized pack and
that is actually ambiguous (example: a new Flipper IR helper).

Do not keep syncing general harness rules (model routing, package-toolkit,
MemPalace, find-patch-loop, illustrated-brochure, compose bind volumes, …)
into specialized packs.

## Do not

- Duplicate a skill into a repo that is not a toolkit.
- Overwrite a toolkit skill that the user has locally patched without saying so.
- Commit from this rule; the user decides when to commit.
- Invent `{HOME}/repos/<name>-toolkit` or guessed sibling names.
