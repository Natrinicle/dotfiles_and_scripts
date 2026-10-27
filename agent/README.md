# Agent Skills Toolkit

Sanitized package of agent skills and rules (Grok/Claude compatible).
Counts and layout match the root `README.md` and `toolkit.yaml`.

## Contents

- **Rules** (34) including `code-quality`, `security`, `subagents-first`,
  `public-api-auth`, `ask-before-remote-actions`,
  `prefer-updates-before-workarounds`, `toolkit-residual-identity`.
- **Skills** (89) covering packaging, scanners, PII detection, MemPalace,
  Flipper IR, compiled-app unpack, forensic cores plus thin server companions,
  and workflow helpers.
- **Hooks** — `agent/hooks/` copies into `{AGENT_HOME}/hooks/`. Register in
  host `settings.json` (see `hooks/README.md`).
- **Writing style** — `nate-writing-style` ships `{user}` placeholder voice
  notes and a multi-party isolation rule. Replace the reference file with your
  own. Directory name is kept for install-path stability.
- **Screenshot style tracker** — careful attribution required.

`court-case-monitor`, product bootcamps, and host-only k8s/ops skills stay
out of this pack. See `examples/EXCLUDED.md`.

## Install

Use the repo-root installer:

```bash
./install.sh --agent
```

That copies rules, skills, and hooks into `~/.claude`, then links Grok.
Existing live files are skipped unless `--force`. Adapt placeholders
(`{user}`, `{company}`) in personal skills if reusing for someone else.

## Placeholders

- `{user}` — replace with your name/handle
- `{company}` — replace with organization names
- `{MEMORY_ROOT}` / `{AGENT_HOME}` — agent config and memory roots
- `${HOME}` — home directory

## Vendor-specific bits

Skills that call `gh`, Slack, Jira, etc. keep CLI names. Org/channel IDs are
abstracted where possible. See root README **Vendor-specific bits**.

## Residual scan

`python3 agent/skills/package-toolkit/scripts/residual-identity-scan.py`
must PASS before commit. Style reference files in this pack are placeholders.
Re-scan if redistributing.
