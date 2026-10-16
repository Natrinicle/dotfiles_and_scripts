---
name: shell-item-activity
description: "Reconstruct folder browsing and file-open activity from Shellbags, LNK files, and Jump Lists. Use when proving access to deleted folders, USB paths, or network shares; chain into expert reports."
type: knowledge
lifecycle: active
---

# Shell Item Activity

Prove interactive navigation or file open even after the target is deleted or the device is disconnected.

## Artifacts

- **Shellbags** (`BagMRU` / `Bags` in NTUSER.DAT or UsrClass.dat): folder paths browsed via Explorer, including removable and network. Last-write approximates last interaction. Survives deletion.
- **LNK files** (`%APPDATA%\Microsoft\Windows\Recent\`): target path, volume serial, MAC address, MACB times. Created on open via Explorer.
- **Jump Lists** (`AutomaticDestinations`): per-application recent files (embedded LNK data).

Shellbags do not record command-line or non-Explorer access. Correlate with Prefetch, USBStor, or event logs.

## Analysis Steps

1. Parse Shellbags for paths of interest (USB, network, deleted staging folders).
2. Collect LNK and Jump List entries for the same paths or filenames.
3. Note volume serials and device identifiers.
4. Cluster by time and correlate with other artifacts.

## Output Format (for chaining)

```
SHELL_ITEMS
shellbags: [ "path (last_write)" ]
lnk_files: [ "target_path (volume_serial)" ]
jump_lists: [ "app: target" ]
conclusion: browsed|opened|none_observed
notes: short bullets
```

## Companions

Windows-centric. Server use is limited to Windows Server hosts with Explorer activity.

When updating, keep path and volume-serial fields stable.
