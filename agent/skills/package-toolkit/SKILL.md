---
name: package-toolkit
description: >
  Use when packaging toolkits, exporting dotfiles, sanitizing home scripts for
  publish, installing a toolkit pack, or deciding whether work is a generic
  shareable pack versus repo-specific product code.
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

Create a **portable toolkit** another person (or future you) can load from a
directory or zip. Supports two product shapes with the same abstraction rules:

| Kind | Examples | Typical output |
|------|----------|----------------|
| **Agent toolkit** | skills, rules, feedback, hooks, MCP stubs, permission notes | `.claude/` / `.grok/` layout + `toolkit.yaml` |
| **Environment toolkit** | bashrc, aliases, `~/.local/bin` scripts | `shell/`, `bin/`, optional `config/` |

## Abstraction philosophy (non-negotiable)

Prefer **role-level** wording over **instance-level** wording so consumers plug
in their own org, user, and paths.

| Prefer | Avoid (unless explicitness is required) |
|--------|----------------------------------------|
| `Lookup IM conversation` | `Lookup Slack conversation` |
| `Use {company}'s API` | `Use Globex's API` (hard-coded employer) |
| `${HOME}/.config/...` | `/home/alice/...` |
| `{user}` / `$USER` | hard-coded login or full name |
| `{company_domain}` | `contoso.com`, `globex.example` |
| `~/.mozilla/firefox/{profile}` | `~/.mozilla/firefox/abc123.default-release` |
| `{default_route_host}` | personal hostnames / LAN names |

**Keep explicit** only when the behavior is vendor-locked and the name *is* the
interface (e.g. `kubectl`, `docker`, `git`). Prefer a comment:
`# Vendor-specific: replace if you use another client`.

## Classify first

Sanitize with this skill when **creating or updating a toolkit**. Decide the
kind before copying anything:

| Kind | Where it lives | Sanitize |
|------|----------------|----------|
| **Generic reusable pack** | `general_pack` (`dotfiles_and_scripts`) or a specialized pack whose domain matches (`remote_codes`, court-case-monitor) | Yes — placeholders, residual scan |
| **Repo-specific product work** | The application repo that owns it (compose, ADRs, services, product hostnames) | Personal tokens only (`${HOME}`, no absolute homes). Keep product names. Land with that repo's PR rules. |

Scrutiny: a laptop compose stack, an ADR, or a service that names `{product}`
is **repo-specific**. Shell helpers, agent skills/rules, and Flipper IR catalogs
are **generic**.

## When to run

- User asks to package, export, sanitize, or publish a toolkit / dotfiles pack
- Preparing a zip/dir for another machine or another person to install
- After large reorganizations of shell config or agent skills meant for reuse
- After classifying an artifact as a generic reusable pack

## Workflow

1. **Classify** — generic pack vs repo-specific product work (table above).
2. **Confirm kind** — agent toolkit, environment toolkit, or both.
3. **Confirm source roots** — e.g. `~/.claude`, `~/.bash_aliases.d`, `~/.local/bin`.
4. **Confirm destination** — existing git repo path from `toolkit-homes.yaml`.
5. **Build inventory** — list files; drop secrets, backups, editor junk, pipx/tool
   symlinks that only exist on this machine.
6. **Sanitize** — run `scripts/sanitize-copy.py` (host denylist tokens become
   `{subject}`; fails if no denylist unless `--allow-missing-denylist`). Or apply
   `references/abstraction-rules.md` by hand.
7. **Write / update** `toolkit.yaml` + `README.md` (layout, benefits, install).
8. **Scan destination** with `scripts/residual-identity-scan.py` (see below).
9. **Local subagent pass** — leftover PII / specific companies the denylist
   does not know. Keep vendor-locked names (`When accessing AWS…`). See below.
10. **Propose commit** in the destination repo (do not force-push unless the user named a history rewrite).

## Default exclude patterns

Never pack:

- `*.swp`, `*~`, `*.bak`, `*.sync-conflict-*`, `.*.swp`
- Known secret files (`.env`, `*credentials*`, vault files, borg passphrases)
- Versioned script backups (`*.2026*`, `*.bak-*`) unless user asks
- Binary tool managers' symlinks under `~/.local/bin` that point into pipx/uv
  (only ship **authored** scripts)
- Company-specific LDAP/SSO helpers that cannot be abstracted — either drop or
  replace with `examples/*.example` using placeholders

## Residual scan (required before commit)

Hard gate. From the pack root:

```bash
python3 agent/skills/package-toolkit/scripts/residual-identity-scan.py
```

The pack pre-commit hook `residual-identity-scan` scans the **whole pack root**
(`pass_filenames: false`; git tracked + untracked-not-ignored). Rule:
`toolkit-residual-identity`.

The script loads a **host** denylist (`{AGENT_HOME}/config/identity-denylist.yaml`)
and optional gitignored `config/identity-denylist.local.yaml`. Authoring **fails**
if no tokens load. CI (`CI` / `GITHUB_ACTIONS`) still runs the email/home scan
without a host file. `--allow-missing-denylist` / `--no-host-denylist` are
test/CI overrides. Do **not** commit real names into the pack.
`config/identity-denylist.example.yaml` uses fake names only.

Also search the tree for:

- Prior usernames, full names, case-party names, emails
- Prior company / product hostnames
- Absolute homes (`/home/…`, `/Users/…`) except in docs explaining `${HOME}`
- Hard-coded profile IDs (Firefox profile dirs)
- Tokens, passphrases, private keys

If any hit is intentional vendor text, document it in README under
**Vendor-specific bits**. Case-party names in forensic example lines are not
vendor text — use `{subject}` / `{account}`.

## Local subagent pass (authoring)

After the residual scan PASSes, hunt names the denylist missed. CI skips this.

```bash
python3 agent/skills/package-toolkit/scripts/identity-subagent-scan.py \
  --root . --out /tmp/identity-bundle.md
# prose (md/yaml) by default; --include-code adds .py/.json
```

Classify the bundle on a **local** model. Prefer:

```bash
python3 agent/skills/package-toolkit/scripts/identity-subagent-scan.py \
  --root . --out /tmp/identity-bundle.md --ollama
```

That POSTs `references/identity-subagent-prompt.md` plus the bundle to
Ollama `gemma4` (`/api/generate`). Do **not** spawn `general-purpose` for this
(16K overflow). If Ollama is down, spawn `local-extract` / `explore` (omit
`model`) with **only** the prompt file plus the bundle.

Keep public interface names (AWS, GitHub, Docker, Traefik, Flipper, Kubernetes)
and README **Vendor-specific bits**. Replace person names, employer/customer
names, and personal domains with `{subject}` / `{company}` / `{user}`. Parent
follows `hits`; ignore over-redaction of vendor names. Escalate a malformed
report once on the parent.

The stdlib residual scan remains the hard gate. This pass is extra recall.

## Install contract

Every package **must** include:

1. `toolkit.yaml` — kind, version, paths, placeholders
2. `README.md` — what/where/why + install steps
3. Optional `install.sh` — copies into `$HOME` / agent config with backups

Agent toolkits should document required **permissions / MCP / settings** as
placeholders, not as another user's live secrets.

## After packaging

Follow `~/.claude/rules/readme-freshness.md`: if the pack content changed, the
README must match. Prefer updating README in the same change set as the files.

## References

- `references/abstraction-rules.md` — replacement tables and naming
- `scripts/sanitize-copy.py` — copy + HOME rewrite + denylist `{subject}`
- `scripts/residual-identity-scan.py` — whole-tree identity gate before commit
- `scripts/identity_denylist.py` — shared host-denylist load/compile/replace
- `scripts/identity-subagent-scan.py` — heuristic bundle + `--ollama` (gemma4)
- `references/identity-subagent-prompt.md` — classify prompt (keep AWS-class names)
- `references/vendor-locked-names.txt` — public cloud/OSS names the heuristic skips

## Permanent exclusions

- **`mouse_mover`** and `~/.bash_aliases.d/work` (ydotool idle mouse) — never package for sharing.
