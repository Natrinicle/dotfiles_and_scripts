---
name: execution-evidence
description: "Determine whether a binary was executed versus merely present, using Prefetch, Amcache, UserAssist, BAM/DAM, and SRUM. Use when an examiner or probable-cause claim equates file existence with program execution; chain into expert reports."
type: knowledge
lifecycle: active
---

# Execution Evidence

Separate “file existed” from “program ran.” Emit an explicit reliability rating.

## Artifacts and what they prove

| Artifact | Proves execution? | Key data | Notes |
|----------|-------------------|----------|-------|
| Prefetch (`.pf`) | Yes | Run count, last 8 times, referenced files | Off by default on Server |
| Amcache | Presence + SHA-1 | Path, hash, first-inventory time | Not alone proof of execution |
| UserAssist | Yes (GUI) | ROT13 path, run count, focus time | Explorer-launched only |
| BAM/DAM | Yes (recent) | Last execution per SID | ~7-day retention |
| SRUM | Yes (usage interval) | Bytes, CPU, user SID | 30–60 days; hourly buckets |
| ShimCache | Presence only (Win10+) | Path, $SI mod time | Do not claim execution |

## Analysis Steps

1. Locate each artifact for the binary of interest.
2. Record whether it shows execution, presence only, or is absent.
3. Note Windows version and Prefetch enablement.
4. Assign an overall reliability: high (Prefetch or BAM + corroboration), medium (UserAssist or SRUM alone), low (Amcache/ShimCache only).

## Output Format (for chaining)

```
EXECUTION_EVIDENCE
binary: "..."
prefetch: present|absent (run_count, last_runs)
amcache: present|absent (sha1)
userassist: present|absent
bam: present|absent
srum: present|absent
shimcache: present|absent
reliability: high|medium|low|none
conclusion: executed|presence_only|unknown
notes: short bullets
```

## Companions

- `server-execution-evidence`

When updating, keep the reliability field and artifact meanings stable for callers.
