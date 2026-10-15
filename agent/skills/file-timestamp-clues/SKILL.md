---
name: file-timestamp-clues
description: "Analyze file system timestamps for NTFS/FAT32 precision differences, copy-vs-create indicators, clock spoofing risks, and access-date spoliation. Use when reviewing forensic file listings, MFT exports, FTK reports, or Windows artifacts for date reliability and evidence of local copies versus fresh downloads."
type: knowledge
lifecycle: active
---

# File Timestamp Clues

Extract reliability signals from Created, Modified, and Accessed timestamps. Prefer structured output for chaining into bandwidth checks or expert reports.

## Core Rules

- **NTFS** (Windows XP default): Created/Modified/Accessed stored to 100-ns / millisecond precision.
- **FAT32** (common USB/flash): Modified precision limited to 2 seconds (even whole seconds, no fractional). Created/Accessed vary.
- Even-second Modified dates on NTFS strongly suggest copy from FAT32 source. Windows preserves source Modified on copy.
- Created date = when the file first appeared *on this volume*. A copy gets a new Created date; original Modified is kept.
- Modified can precede Created after a copy. Windows does not enforce consistency.
- Access dates are frequently overwritten by later activity (antivirus, indexing, user browsing). Treat as spoiled unless corroborated.
- System clock can be changed by a novice in minutes. Brief clock set → copy → restore produces arbitrary Created dates with no other artifacts.

## Analysis Steps

1. Note the file system of the examined volume (NTFS vs FAT).
2. For each file of interest, record Created, Modified, Accessed (if present) and fractional seconds.
3. Flag any Modified timestamp that is an even whole second (…:00 or …:02 … :58) as likely FAT32 origin.
4. Cluster files by Created time. Tight clusters of many large files → copy batch, not sequential downloads.
5. Compare Created vs Modified. Modified < Created is normal for copies.
6. Check for later Access dates across the majority of files → temporal spoliation of Access metadata.
7. Note absence of supporting evidence (Event Logs, Registry last-write, Prefetch, etc.) for claimed install or reformat dates.

## Output Format (for chaining)

```
TIMESTAMP_CLUES
files_examined: N
filesystem: NTFS|FAT32|unknown
even_second_modified: true|false  (count if true)
created_clusters: [ "YYYY-MM-DD HH:MM:SS ±Nmin (M files, X GB)" ]
access_spoliation: high|medium|low|none  (pct after relevant period)
clock_spoof_possible: true|false
notes: short bullet list
```

## Reference

See `references/timestamp-rules.md` for expanded examples from typical Windows XP / LimeWire-era cases.

## Companions

- `server-timestamp-clues`

Server-admin thin companions exist and should be preferred when the context is operational rather than purely forensic. When updating this skill, verify compatibility with all companions and other callers; split only if needs have diverged, with a convergence plan.
