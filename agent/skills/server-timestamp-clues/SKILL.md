---
name: server-timestamp-clues
description: "Server and Linux companion to file-timestamp-clues. Apply core timestamp rules then add ext4/xfs/btrfs, stat, journal, and auditd checks for change detection and bulk-copy analysis on servers. Use when investigating file appearance times, config changes, or unexpected copies on Linux/Windows Server hosts."
type: knowledge
lifecycle: active
---

# Server Timestamp Clues

Thin companion to `file-timestamp-clues`. Always apply the core skill first, then layer server-specific artifacts.

## When to use the core

Load and follow `file-timestamp-clues` for NTFS/FAT precision, copy semantics, Access spoliation, and clock-spoof patterns. Its `TIMESTAMP_CLUES` output remains valid.

## Server additions

- Linux: `stat`, `debugfs -R 'stat <inum>'`, `xfs_io`, `btrfs` subvolume creation times.
- Precision: ext4 has nanosecond `crtime` (when enabled); xfs/btrfs similar. Absence of sub-second data is still a signal.
- Journals: `journalctl`, `/var/log/audit/audit.log` (auditd), systemd unit start times.
- Bulk copies: tight `crtime`/`birth` clusters of many files + preserved `mtime` = local copy (rsync -a, cp -a, tar) rather than package install or git checkout.
- Container/image layers: creation time of image vs. runtime file birth.

## Output

Extend the core block:

```
TIMESTAMP_CLUES
...core fields...
server_context: linux|windows-server|container
birth_cluster: "..."
journal_corroboration: true|false|absent
notes: ...
```

## Upstream note

Changes to `file-timestamp-clues` must keep `TIMESTAMP_CLUES` compatible or this companion (and any other caller) must be updated in the same change.
