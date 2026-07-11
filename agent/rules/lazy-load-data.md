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
| Browser automation | browser automation notes / chrome spawn patterns |
| Local tracing / OTEL demos | local observability setup notes |
| Model routing / cost audits | `model-routing-table.md` |
| Contacts / messaging analysis | contacts profiles (store carefully; may contain PII) |

Do not list secrets, tokens, or private hostnames in always-loaded files.
