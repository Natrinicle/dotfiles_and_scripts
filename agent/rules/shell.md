---
paths:
  - "**/*.sh"
  - "**/*.bash"
  - "**/bashrc*"
  - "**/bash_aliases*"
---

# Shell Scripts

- After edits: `shellcheck` then `shfmt -w` when available
- Use `set -euo pipefail` at the top of scripts
- Quote expansions: `"$var"` not `$var`
- Prefer `[[ ]]` in bash
- Never `eval` untrusted input
- Prefer `$(...)` over backticks
