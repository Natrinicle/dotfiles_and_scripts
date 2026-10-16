---
paths:
  - "**"
---

# Toolkit residual identity scan

Hard gate on **toolkit** commits (a tree with `toolkit.yaml` / `TOOLKIT.md`,
or `agent/skills/` + pack README). Shareable packs must not name real people,
case parties, employers, personal domains, or emails.

## Before commit / push / `gh pr create` in a toolkit repo

1. Run `python3 agent/skills/package-toolkit/scripts/residual-identity-scan.py`
   from the pack root (pre-commit hook `residual-identity-scan` does this).
2. Load the **host** denylist `{AGENT_HOME}/config/identity-denylist.yaml`
   (this machine also `~/.claude/config/identity-denylist.yaml`). Optional
   gitignored `config/identity-denylist.local.yaml` in the repo.
3. **Follow** hits: replace with `{subject}`, `{account}`, `{company}`,
   `{user}`, `{company_domain}`, or drop the sentence. Re-run until PASS.
4. Do **not** put denylist tokens into the pack, the example YAML, tests, or
   commit messages. Example file uses fake names only (`Alice Example`).

## What the scanner flags

- Host/local denylist tokens (case-insensitive word match)
- Emails outside `example.com` / documented placeholders
- Absolute `/home/<login>` and `/Users/<login>` except example/container
  logins (`alice`, `worker`, …). Keep `${HOME}`.

Vendor-locked interface names already listed under README **Vendor-specific
bits** stay. Forensic example lines use `{subject}` / `{account}`.

Run this gate on the current tree as well as after any history rewrite.
