---
paths:
  - "**"
---

# Pre-commit config gate

Hard gate. In the git toplevel of the repo you are changing, if any of
`.pre-commit-config.yaml`, `.pre-commit-config.yml`, or `.pre-commit.yaml`
exists:

1. Read `{MEMORY_ROOT}/pre-commit-gate.md`.
2. Run `pre-commit` on the files you changed (`--files`; see that note for
   `--all-files` and staged-only hooks).
3. **Follow** auto-fixes and real failures: apply them, re-run until clean.
4. If a finding does **not** make sense here (wrong exclude, info-level
   noise, hook that self-skips as Passed, allowlist that would hide a
   scanner): **stop and prompt the user**. Propose a config or rule change.
   Do not `SKIP`, allowlist, or `--no-verify` on your own.

Do not `pre-commit install` unless asked. Missing `pre-commit` binary: say
so; do not skip silently.

Runs after you edit files, and again before commit or `gh pr create`.
User override (“skip pre-commit this run”) still gets reported.
