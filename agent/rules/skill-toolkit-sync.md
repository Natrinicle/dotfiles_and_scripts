# Sync skill and rule updates into toolkits

When you **create or edit a skill or a rule**, copy that change into the
**general pack** in the same turn. Then **ask** whether specialized packs
should get the same update.

Load **package-toolkit** for layout, sanitization, and `toolkit.yaml` /
README freshness. Do not skip the copy because the home skill already exists.

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

## Specialized packs (prompt)

After the general-pack copy, **prompt** before touching specialized packs
listed in `toolkit-homes.yaml`. Do not assume a yes. Do not push.

## Do not

- Duplicate a skill into a repo that is not a toolkit.
- Overwrite a toolkit skill that the user has locally patched without saying so.
- Commit from this rule; the user decides when to commit.
- Invent `{HOME}/repos/<name>-toolkit` or guessed sibling names.
