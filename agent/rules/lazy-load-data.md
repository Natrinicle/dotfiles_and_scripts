# Lazy-Load Large Reference Data

Keep always-on context small. Store large reference material outside the main memory index and load it only when the task needs it.

**Memory root:** `{MEMORY_ROOT}` — typically `~/.claude/memory` or `~/.grok/memory` (often the same directory via symlink).

## When to lazy-load
- API catalogs, repo maps, long runbooks
- Security findings catalogs
- Person/contact profiles and communication notes
- Tool-specific setup guides (browser automation, local observability stacks)
- Model routing tables and cost sheets

## Pattern
1. Keep a short **trigger** in a rule or MEMORY index (one line: when to load + path).
2. Put the full content in a separate markdown file under `{MEMORY_ROOT}/`.
3. Read that file only when the trigger matches.

## Suggested categories (adapt names to your workspace)
| Trigger | Example path under `{MEMORY_ROOT}` |
|---------|-------------------------------------|
| Working in a large monorepo | `workspace-repos.md`, `platform-repo-structure.md` |
| Security review of any code | `vulnerability-patterns.md` |
| Building or exposing a host / VM / cluster | rule `system-security`; `vulnerability-patterns.md` |
| Looking up an API, CLI, device, MCP, library, or protocol | rules `prefer-mempalace` + `mempalace-file-interfaces`; search palace first, then file methods |
| Durable facts vs local memory files | rule `prefer-mempalace`; palace KG / newest `filed_at` wins |
| Preference / fact replacements over time | rule `mempalace-timeline-supersede`; `{MEMORY_ROOT}/mempalace-recency-and-preferences.md` |
| Browser automation | browser automation notes / chrome spawn patterns |
| Local tracing / OTEL demos | local observability setup notes |
| Model routing / cost audits | `model-routing-table.md` |
| Packaging a toolkit | `toolkit-homes.md`; classify first; rule `toolkit-residual-identity` (host denylist, never pack real names) |
| Opening a PR in the current employer's GitHub org | rule `employer-pr-findings-gate`; `{MEMORY_ROOT}/employer-pr-findings-gate.md` |
| Repo has a pre-commit config | rule `pre-commit-gate`; `{MEMORY_ROOT}/pre-commit-gate.md` |
| gitleaks / hadolint canaries or CI CLI install (any repo) | `{MEMORY_ROOT}/scanner-self-test-correctness.md`; palace `kg_query` `gitleaks` / `hadolint`; charset `A-Z2-7` not `A-Z0-9` |
| Contacts / messaging analysis | contacts profiles (store carefully; may contain PII) |
| Change comparisons / Meld-style diffs / YAML JSON dyff | skill `meld-style-diff` |

Do not list secrets, tokens, or private hostnames in always-loaded files.
