---
name: server-volume-provenance
description: "Server companion to reformat-volume-evidence. Reuse volume-creation and earliest-activity checks for detecting unexpected reimages, validating golden images, and confirming disk provenance on servers."
type: knowledge
lifecycle: active
---

# Server Volume Provenance

Thin companion to `reformat-volume-evidence`.

## Core reuse

Follow `reformat-volume-evidence` for earliest system activity vs. claimed events and the `REFORMAT_EVIDENCE` block.

## Server artifacts

- Filesystem UUID / creation time (`blkid`, `tune2fs -l`, `xfs_info`)
- OS install logs, cloud-init, ignition, Packer/Terraform apply times
- Sudden restart of file birth times = reimage
- Golden-image validation: expected build date vs. observed

## Output

Same `REFORMAT_EVIDENCE` block; add `provenance: golden-image|manual|cloud-init|unknown`.

## Upstream note

“Earliest activity vs. claim” logic is shared.
