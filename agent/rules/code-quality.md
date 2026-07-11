# Code Quality

## When to run tools
1. After you write or change code — format/lint before presenting results
2. When reviewing someone else's code — report findings; ask before bulk auto-fix
3. Before commits or PRs
4. When asked to check, lint, or assess security of code

## Your edits
1. Change the code
2. Run project formatters and linters with auto-fix where safe
3. Re-run to confirm clean
4. Say what ran and what changed

## Reviewing others' code
1. Run analysis
2. Explain findings
3. Ask before applying automatic fixes

## Pre-commit
1. Format changed files
2. Lint with fix
3. Verify check mode is clean
4. Re-stage formatter output

## Overrides
- "don't lint" → skip lint
- "skip formatters" → skip format; still consider security checks if relevant
- "just the code" → deliver without tool runs; note that it was not validated
