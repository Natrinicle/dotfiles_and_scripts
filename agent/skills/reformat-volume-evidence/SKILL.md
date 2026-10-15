---
name: reformat-volume-evidence
description: "Test a claimed hard-drive reformat or Windows reinstall by examining volume creation time, Windows install artifacts, and the volume of pre-existing files. Use when a probable-cause statement asserts a reformat during a relevant period; chain into expert reports."
type: knowledge
lifecycle: active
---

# Reformat / Volume-Creation Evidence

Determine whether a hard drive was reformatted or Windows was reinstalled during a claimed period.

## Positive Indicators of Earlier Install

- Large number of files with Created dates well before the claimed reformat
- Windows folder, Program Files, and user profile creation dates clustering on an earlier date
- Absence of volume-creation or format-related Event Log entries in the claimed window
- Consistent MFT record numbers and file density inconsistent with a recent format

## Negative Indicators

- No sudden drop-off or restart of file creation at the claimed reformat date
- System files and application folders predating the claim

## Analysis Steps

1. Identify the earliest substantial cluster of system and user file Created dates.
2. Count files predating the claimed reformat.
3. Check for any format, chkdsk, or setup Event Log entries in the claimed window.
4. Note the Windows installation date if recoverable from Registry or setup logs.
5. Conclude whether the claim is supported.

## Output Format (for chaining)

```
REFORMAT_EVIDENCE
claimed_reformat: YYYY-MM-DD or none
earliest_system_activity: YYYY-MM-DD
files_predating_claim: N
supporting_evidence_found: true|false
conclusion: no_reformat|reformat_supported|inconclusive
notes: short bullets
```

## Reference

See `references/example.md` for the April 2007 install vs claimed 2008 reformat.

## Companions

- `server-volume-provenance`

Server-admin thin companions exist and should be preferred when the context is operational rather than purely forensic. When updating this skill, verify compatibility with all companions and other callers; split only if needs have diverged, with a convergence plan.
