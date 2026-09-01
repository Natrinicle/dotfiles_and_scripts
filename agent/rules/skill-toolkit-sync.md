---
paths:
  - "**/.claude/skills/**"
  - "**/.grok/skills/**"
  - "**/agent/skills/**"
  - "**/SKILL.md"
  - "**/.claude/rules/**"
  - "**/.grok/rules/**"
  - "**/agent/rules/**"
---

# Sync skill and rule updates into toolkits

When you **create or edit a skill or a rule**, copy that change into the
**current repo's toolkit** in the same turn. Then **ask** whether other
toolkit repos should get the same update.

Load **package-toolkit** for layout, sanitization, and `toolkit.yaml` / README
freshness. Do not skip the copy because the home skill already exists.

## What counts as a toolkit repo

Any of:

- `toolkit.yaml` or `TOOLKIT.md` at the repo root
- `agent/skills/` or `agent/rules/` (portable agent pack)
- `.claude/skills/` plus a pack README that documents those skills

## Current repo (automatic)

1. Find the toolkit skill/rule directory:
   - `agent/skills/` and `agent/rules/` if present
   - else `.claude/skills/` and `.claude/rules/` (Grok copies often symlink
     `.grok/skills` here)
2. Copy the updated skill **tree** (`SKILL.md`, `references/`, `scripts/`) or
   the updated `*.md` rule into that directory, same relative name.
3. If `package-toolkit` sanitization applies (shareable pack), strip homes,
   logins, and employer names per that skill.
4. If `toolkit.yaml` exists, bump `version` when the public surface changed,
   and keep `agent_skills_included` / `agent_rules_included` accurate.
5. Update the toolkit `README.md` in the same change when install paths,
   counts, or listed skills/rules changed (`readme-freshness`).

Do this even when the edit started in `{AGENT_HOME}/skills` or
`{AGENT_HOME}/rules` (home Claude/Grok trees). The current working repo still
gets the copy if it is a toolkit.

## Other toolkit repos (prompt)

After the current-repo copy, **prompt the user** before touching anywhere
else. List candidates you can see (sibling checkouts with `toolkit.yaml`,
repos this skill already lives in) as a short yes/no, for example:

- Update `{other_toolkit_repo}` as well?
- Skip other repos this time?

Do not push, and do not assume a yes. If they agree, copy the same skill/rule
tree there with the same sanitization and README/`toolkit.yaml` bump.

## Do not

- Duplicate a skill into a repo that is not a toolkit (no `toolkit.yaml`, no
  `agent/skills`, no documented `.claude/skills` pack).
- Overwrite a toolkit skill that the user has locally patched without saying so.
- Commit from this rule; the user decides when to commit.
