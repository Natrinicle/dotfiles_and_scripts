---
name: identical-folder-copy-indicators
description: "Detect identical folder trees via matching names, sizes, subfolder structure, and cryptographic hashes as evidence one is a copy of the other. Use when comparing multiple locations of the same content (e.g. LimeWire downloads folders) in forensic file listings or hash reports; chain into expert reports."
type: knowledge
lifecycle: active
---

# Identical Folder Copy Indicators

Identify when two or more folder trees contain identical content, proving a copy relationship independent of timestamps.

## Core Indicators

- Matching folder and subfolder names
- Matching file names
- Matching file sizes
- Matching cryptographic hashes (MD5, SHA1, SHA256)
- Same total file count

Presence of all four (names + sizes + hashes + structure) is conclusive that the folders are copies of each other.

## Analysis Steps

1. Locate candidate folders (e.g. multiple “Limewire downloads” paths).
2. Compare structure (subfolder names and nesting).
3. Compare file lists (names and sizes).
4. Compare hash values when available.
5. Note the earlier Created date of the source folder if timestamps are reliable.
6. Record the later destination path.

## Output Format (for chaining)

```
IDENTICAL_CONTENT
source_path: "..."
destination_path: "..."
file_count: N
total_size: X GB
hash_match: true|false|partial
structure_match: true|false
conclusion: copy|not_copy|inconclusive
notes: short bullets
```

## Reference

See `references/examples.md` for the dual LimeWire downloads folders case.

## Companions

- `server-duplicate-detection`

Server-admin thin companions exist and should be preferred when the context is operational rather than purely forensic. When updating this skill, verify compatibility with all companions and other callers; split only if needs have diverged, with a convergence plan.
