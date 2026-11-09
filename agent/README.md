# Agent Skills Toolkit

Sanitized package of agent skills and rules (Grok/Claude compatible).
Counts and layout match the root `README.md` and `toolkit.yaml`.

## Contents

- **Rules** (43) including `code-quality`, `security`, `subagents-first`,
  `prefer-subagents-before-compaction`,
  `public-api-auth`, `ask-before-remote-actions`,
  `prefer-helper-scripts`, `prefer-updates-before-workarounds`,
  `toolkit-residual-identity`,
  `expected-value`, `agent-graphs`, `cups-custom-backend`, `mempalace-compact-filing`,
  `claim-source-check`, `skill-composition` (merged-skill routing).
- **Skills** (134) covering packaging, scanners, PII detection, MemPalace,
  Flipper IR, compiled-app unpack, forensic cores plus thin server companions,
  expected-value spend gate, agent graphs (`agent-graphs` / `loop-until-green`),
  clean-room reconstruct (`clean-room-reconstruct`),
  leftover account sessions (`leftover-account-sessions`),
  Kubernetes control-plane WAN gate (`k8s-control-plane-vpn`),
  CUPS custom-backend persist, claim-source-check,
  merged public skills (`grilling`, `security-audit`, `egm-*`,
  `obsidian-*`, and others — see `THIRD-PARTY.md`),
  and workflow helpers.
- **Agents** (10) — EGM Goldfish personas in `agent/agents/` →
  `{AGENT_HOME}/agents/`.
- **Resources** — shared checklists and EGM document standards in
  `agent/resources/` → `{AGENT_HOME}/resources/`.
- **Third-party notices** — `THIRD-PARTY.md` (MIT ×4 + Apache-2.0 EGM).
- **Hooks** — `agent/hooks/` copies into `{AGENT_HOME}/hooks/`. Register in
  host `settings.json` (see `hooks/README.md`). Includes
  `control-plane-exposure.py` and `prefer-spawn-search.py`.
- **Writing style** — `nate-writing-style` ships `{user}` placeholder voice
  notes and a multi-party isolation rule. Replace the reference file with your
  own. Directory name is kept for install-path stability.
- **Screenshot style tracker** — careful attribution required.

`court-case-monitor`, product bootcamps, and host-only k8s/ops skills
(CNI, PVC, Helm, …) stay out of this pack. Generic
`k8s-control-plane-vpn` is packed. See `examples/EXCLUDED.md`.

## Install

Use the repo-root installer:

```bash
./install.sh --agent
```

That copies rules, skills, hooks, agents, and resources into `~/.claude`,
then links Grok. Existing live files are skipped unless `--force`. Adapt
placeholders (`{user}`, `{company}`) in personal skills if reusing for
someone else.

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
