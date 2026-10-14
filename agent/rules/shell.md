---
paths:
  - "**/*.sh"
  - "**/*.bash"
  - "**/bashrc*"
  - "**/bash_aliases*"
---

# Shell Scripts

- If **pre-commit-gate** applies, that run is the first lint
- After edits: `shellcheck` then `shfmt -w` when available unless pre-commit already ran those hooks on this file
- Use `set -euo pipefail` at the top of scripts
- Quote expansions: `"$var"` not `$var`
- Prefer `[[ ]]` in bash
- Never `eval` untrusted input
- Prefer `$(...)` over backticks
