# Third-party agent skills

Inbound copies merged into this pack on 2026-11-08. They sit in the same
`agent/skills`, `agent/agents`, and `agent/resources` trees as the rest of
the pack. There is no internal/external split.

Each copied skill directory includes the upstream `LICENSE`. This file is
the pack-level notice. Copyright lines in those LICENSE files stay as
upstream wrote them.

Clones used for the copy live under `{HOME}/repos/external` (read-only
mirrors). Do not push those remotes.

## Matt Pocock skills (MIT)

- Upstream: https://github.com/mattpocock/skills
- Snapshot: `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d` (2026-10-31)
- Copyright: Copyright (c) 2026 Matt Pocock
- License: MIT (copy in each skill dir)

Packed skills: `grilling`, `wait-what`, `wayfinder`, `codebase-design`,
`writing-for-agents`, `wizard`, `to-questionnaire`, `prototype`,
`to-tickets`, `domain-modeling`.

Skipped as duplicates of pack skills already here: TDD, code-review,
diagnosing-bugs, git-guardrails, and related wrappers.

## Addy Osmani agent-skills (MIT)

- Upstream: https://github.com/addyosmani/agent-skills
- Snapshot: `301b02b12bff98e4688e6984af6556802322bbde` (2026-11-01)
- Copyright: Copyright (c) 2025 Addy Osmani
- License: MIT (copy in each skill dir and `agent/resources/LICENSE`)

Packed skills: `interview-me`, `doubt-driven-development`,
`constraint-driven-development`, `source-driven-development`,
`code-simplification`, `idea-refine`, `shipping-and-launch`,
`deprecation-and-migration`, `browser-testing-with-devtools`.

Shared checklists from upstream `references/` are at `agent/resources/`
(`testing-patterns.md`, `orchestration-patterns.md`,
`accessibility-checklist.md`, `performance-checklist.md`,
`definition-of-done.md`, `observability-checklist.md`,
`security-checklist.md`). Skill bodies that pointed at
`../../references/` now point at `../../resources/`.

## Cloudflare security-audit (MIT)

- Upstream: https://github.com/cloudflare/security-audit-skill
- Snapshot: `c1c8a8c1471069fb0e188eeaff69b8e8db6564a8` (2026-09-14)
- Copyright: Copyright (c) 2025-2026 Cloudflare, Inc.
- License: MIT (copy in `agent/skills/security-audit/LICENSE`)

Packed skill: `security-audit` (coverage-ledger / `findings.json`; no
patcher). Complements pack `find-patch-loop`. See
`agent/rules/skill-composition.md`.

## kepano Obsidian skills (MIT)

- Upstream: https://github.com/kepano/obsidian-skills
- Snapshot: `3ccff5338ea700537839b21900aa5358a0402c98` (2026-09-15)
- Copyright: Copyright (c) 2026 Steph Ango (@kepano)
- License: MIT (copy in each skill dir)

Packed skills: `obsidian-markdown`, `obsidian-bases`, `json-canvas`,
`obsidian-cli`, `defuddle`, `knap`.

These cover Obsidian Flavored Markdown, Bases, JSON Canvas, and the
`obsidian` CLI. A vault-host plugin is a different skill.

## Google Elephant-Goldfish Model (Apache-2.0)

- Upstream: https://github.com/google/elephant-goldfish-model
- Snapshot: `51cfc424b91c483d39e65984124cd782ab998e3c` (2026-11-09)
- Copyright: Copyright 2026 Google LLC
- License: Apache License 2.0 (copy in each `egm-*` skill dir,
  `agent/agents/LICENSE`, and `agent/resources/egm/LICENSE`)
- NOTICE: upstream ships no `NOTICE` file. This section is the
  NOTICE-equivalent for the packed copy.

Packed skills: `egm-brainstorm`, `egm-draft`, `egm-review`,
`egm-review-loop`, `egm-resolve`, `egm-bootstrap`, `egm-drift-report`.

Personas: `agent/agents/*.md` (10 files).

Standards and harness docs: `agent/resources/egm/`
(`document_standards/`, `execution_instructions.md`, `docs/`).

Goldfish review is a fresh-context design-doc pass. It is not
`independent-checker`, `check-work`, or `speckit`. See
`agent/rules/skill-composition.md`.

### Modified files (Apache-2.0 §4(b))

Path rewrites so flattened `agent/skills/<name>/SKILL.md` can read
`agent/agents` and `agent/resources/egm` (two directories up). Each
modified `SKILL.md` also carries an HTML comment
`Pack path adapt 2026-11-08`.

- `agent/skills/egm-brainstorm/SKILL.md`
- `agent/skills/egm-draft/SKILL.md`
- `agent/skills/egm-review/SKILL.md`
- `agent/skills/egm-review-loop/SKILL.md`
- `agent/skills/egm-resolve/SKILL.md`
- `agent/skills/egm-bootstrap/SKILL.md`
- `agent/skills/egm-drift-report/SKILL.md`
- `agent/resources/egm/docs/claude.md` (pack-path note in the file
  header comment)

Rewrites: `${CLAUDE_PLUGIN_ROOT}` / plugin-root `docs/` and
`../../../../agents/` → `../../resources/egm/docs/…` and
`../../agents/…`.

## Routing

Do not keep a second copy of these skills in an “external pack” or
`examples/` ghetto. Rules and routing notes stay global under
`agent/rules/` (`skill-composition`).
