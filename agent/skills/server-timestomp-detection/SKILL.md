---
name: server-timestomp-detection
description: "Server/Linux companion to timestomp-detection. Apply core $SI/$FN logic where available, then add ext4/xfs crtime vs mtime/ctime checks and journal corroboration for backdated files on Linux hosts."
type: knowledge
lifecycle: active
---

# Server Timestomp Detection

Thin companion to `timestomp-detection`. Apply the core skill first when the volume is NTFS; layer Linux-specific checks otherwise.

## Server additions

- ext4: `debugfs -R 'stat <inum>'` or `stat` for `crtime` (birth) vs `mtime`/`ctime`. `crtime` later than claimed activity or `mtime` earlier than `crtime` after a known copy is a signal.
- xfs/btrfs: equivalent birth times via `xfs_io` or subvolume metadata.
- Journals: `journalctl` or auditd records that post-date a claimed file creation.
- Package-install or container-layer timestamps that contradict a backdated binary.

## Output

Same `TIMESTOMP_FLAGS` block; add `filesystem: ext4|xfs|btrfs|ntfs|other` and `birth_source: debugfs|stat|journal`.

## Upstream note

Core inversion and zero-subsecond rules must stay compatible.
