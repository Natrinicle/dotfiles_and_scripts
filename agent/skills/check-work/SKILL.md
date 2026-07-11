---
name: check-work
description: >
  Verify session work with a verifier subagent: checklist, evidence, builds/tests,
  VERDICT PASS/FAIL. Use for /check-work, /verify, self-check.
---

# Check Work

## Modes

- **Same-turn:** finish the user task first, then verify.  
- **Standalone:** verify the current session’s work immediately.  

Optional focus area narrows the verdict.

## Loop

1. Spawn a general-purpose verifier (description prefix `[checking my work]`).  
2. Pass a prompt that requires:  
   - Restate requirements as a checklist (all task types, not only code)  
   - Reconstruct actions vs claims  
   - Independently inspect the environment (read files, run commands)  
   - If code: diff, build, test, lint per project docs  
   - End with exactly `VERDICT: PASS` or `VERDICT: FAIL` plus issues  
3. On FAIL: fix and re-verify (cap ~3).  
4. On PASS: summarize evidence; stop.  

## Principles for the verifier

- Outcomes over effort; no proxy-only success.  
- Broken build/tests → FAIL for code tasks.  
- Do not invent nits; policy in AGENTS/CLAUDE.md counts as FAIL.  
- Temporary verify artifacts are fine.
