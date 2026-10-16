---
name: timestomp-detection
description: "Detect deliberate timestamp manipulation (timestomping) on NTFS by comparing $STANDARD_INFORMATION vs $FILE_NAME attributes, zeroed sub-second precision, and USN Journal contradictions. Use when file timestamps look inconsistent with surrounding activity or when anti-forensics is suspected; chain after file-timestamp-clues."
type: knowledge
lifecycle: active
---

# Timestomp Detection

Identify signs that file timestamps were deliberately altered. Builds on `file-timestamp-clues`. Output a structured block for chaining.

## Core Indicators (strongest first)

- `$STANDARD_INFORMATION` Created earlier than `$FILE_NAME` Created — logically impossible on an unaltered volume (file cannot be named after it was created).
- Sub-second (nanosecond) fields all zero on `$SI` timestamps while surrounding files have noise — common automated-tool signature.
- `$SI` timestamps predate the OS install or contradict recent USN Journal / `$LogFile` records for the same MFT entry.
- PE compile time later than any `$SI` timestamp on the binary (optional corroboration).

False positives exist: some installers, archive extractors, and volume-local renames can produce `$SI`/`$FN` mismatches. Treat inversion as a strong lead, not proof of intent.

## Analysis Steps

1. Parse MFT (or equivalent) for the file of interest.
2. Compare `$SI` Created vs `$FN` Created.
3. Check sub-second precision on `$SI` times.
4. Cross-check against USN Journal records for the MFT entry if available.
5. Note any matching legitimate system-file timestamps (common APT pattern).

## Output Format (for chaining)

```
TIMESTOMP_FLAGS
file: "..."
si_created_before_fn: true|false
zero_subsecond: true|false
usn_contradiction: true|false|absent
pe_compile_after_si: true|false|n/a
conclusion: likely_timestomp|possible|none_observed
notes: short bullets
```

## Companions

- `server-timestomp-detection`

When updating this skill, verify compatibility with companions and callers; split only if needs have diverged.
