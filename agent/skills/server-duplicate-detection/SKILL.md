---
name: server-duplicate-detection
description: "Server companion to identical-folder-copy-indicators. Reuse hash/name/size matching for duplicate data, backup verification, and config drift on servers. Use when comparing directory trees, finding stray copies, or validating backups."
type: knowledge
lifecycle: active
---

# Server Duplicate Detection

Thin companion to `identical-folder-copy-indicators`.

## Core reuse

Apply `identical-folder-copy-indicators` for name + size + structure + hash comparison and the `IDENTICAL_CONTENT` block.

## Server uses

- Backup verification (source vs. backup tree)
- Finding stray copies of secrets, configs, or data sets
- Config drift between hosts or golden image vs. running system
- Tools: `sha256sum`, `rclone check`, `rsync -n -c`, `fdupes`, `jdupes`

## Output

Same `IDENTICAL_CONTENT` block. Add `purpose: backup-verify|drift|stray-copy|other` when clear.

## Upstream note

Hash-match semantics and output format are shared; keep them compatible.
