---
name: package-toolkit
description: >
  Package agent toolkits or environment packs into a sanitized shareable tree.
  Abstracts personal paths and org names. Use when deciding generic pack vs
  repo-specific product work. Helpers belong on PATH.
---

# Package Toolkit

## Where the general pack lives

Host layouts differ. Do not hardcode a checkout path in this skill.

When the user says **make a toolkit**, **package this skill as a toolkit**, or
**add this to the toolkit**:

1. Read `{AGENT_HOME}/config/toolkit-homes.yaml`. Fallback:
   `~/.claude/config/toolkit-homes.yaml`, then `{MEMORY_ROOT}/toolkit-homes.md`.
   Example: `references/toolkit-homes.example.yaml`.
2. Copy into `general_pack` / `skill_dir` (or `rule_dir`). If that pack’s
   `toolkit.yaml` sets `paths.agent_skills`, use that.
3. Bump `toolkit.yaml` `version` and `agent_skills_included`.
4. Update `README.md` (count and listing).
5. Keep the live copy under `{AGENT_HOME}/skills/` and symlink Grok.

Do **not** create `{HOME}/repos/<name>-toolkit`. Do **not** invent sibling
names. If the YAML is missing, ask.

Specialized packs listed under `specialized_packs` are **domain-only**. Copy
there only when the artifact belongs to that pack or is something it already
ships. Do not prompt “update specialized packs too?” after a general-pack
copy. See `skill-toolkit-sync`.

## Kinds

| Kind | Contents |
|------|----------|
| Agent | rules, skills, PATHS conventions |
| Environment | shell startup, aliases, `bin/` helpers |

## Abstraction

- `${HOME}`, `{MEMORY_ROOT}`, `{AGENT_HOME}` over absolute homes  
- `{company}` only as a placeholder, never a real employer name in exports  
- Role-level wording when vendor is incidental  
- Keep real CLI names when the CLI is the interface  

## Classify first

Sanitize when creating or updating a **toolkit**. Decide the kind before copying:

| Kind | Where it lives |
|------|----------------|
| Generic reusable pack | `general_pack` from `toolkit-homes.yaml`, or a specialized pack whose domain matches |
| Repo-specific product work | The application repo (compose, ADRs, services, product hostnames). Residual-scan personal tokens. Keep product names. |

A laptop compose stack or ADR that names `{product}` stays in that product repo.

## Workflow

1. Classify (table above)
2. Inventory; drop secrets, backups, and package-manager symlinks
3. `scripts/sanitize-copy.py` + abstraction rules
4. `toolkit.yaml` + README (keep README fresh with content)
5. Residual-scan: `scripts/residual-identity-scan.py` (host denylist + emails + absolute homes). Rule `toolkit-residual-identity`. Do not commit real names.

## Install contract

`toolkit.yaml`, README, preferably `install.sh` with backups.  
Scripts install to **`~/.local/bin`**, not vendor `scripts/` dirs.
