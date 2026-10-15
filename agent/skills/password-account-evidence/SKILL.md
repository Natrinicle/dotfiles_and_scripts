---
name: password-account-evidence
description: "Search for positive or negative evidence that a Windows user account was password-protected. Use when witness statements or probable-cause claims assert an account was password-protected but Registry or other artifacts may contradict; chain into expert reports."
type: knowledge
lifecycle: active
---

# Password-Protected Account Evidence

Evaluate claims that a specific Windows user account was password-protected.

## Places to Check

- SAM hive / user account flags (if available and not encrypted)
- Presence or absence of password-related Registry values under the user profile
- Login success/failure Event Log patterns
- Witness statements versus artifact support
- Whether the account was used before and after the relevant period without interruption

## Analysis Approach

1. Identify the claimed password-protected account name.
2. Search available Registry, Event Logs, and profile artifacts for password indicators.
3. Note any evidence the account was used both before and after the relevant period.
4. Record the absence of supporting artifacts when none are found.
5. Distinguish “no evidence found” from “evidence of no password.”

## Output Format (for chaining)

```
PASSWORD_EVIDENCE
account: "..."
claimed_protected: true|false
artifacts_supporting_claim: true|false
artifacts_contradicting: true|false
conclusion: supported|unsupported|inconclusive
notes: short bullets
```

## Reference

See `references/example.md` for a sample password-protection claim.

## Companions

- `server-account-audit`

Server-admin thin companions exist and should be preferred when the context is operational rather than purely forensic. When updating this skill, verify compatibility with all companions and other callers; split only if needs have diverged, with a convergence plan.
