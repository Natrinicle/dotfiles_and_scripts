---
name: usb-device-history
description: "Extract and list USB devices previously connected to a Windows system from the Registry USBStor key, including device descriptions and serial numbers. Use when reviewing Windows Registry exports or forensic images for external storage, cameras, phones, or other USB devices; chain into expert reports."
type: knowledge
lifecycle: active
---

# USB Device History

Recover the list of USB storage and other devices that have been connected to a Windows computer.

## Primary Location

`ControlSet001\Enum\USBStor` (also check ControlSet002 and CurrentControlSet if present)

Each subkey typically contains:
- Device description (FriendlyName or DeviceDesc)
- Serial number (often in the key name or a value)

## Analysis Steps

1. Locate the USBStor key in the Registry hive.
2. Enumerate subkeys.
3. Extract device description and serial number for each.
4. Note any duplicates or partial serials.
5. Present as a clean table.

## Output Format (for chaining)

```
USB_DEVICES
count: N
devices:
  - description: "..."
    serial: "..."
notes: short bullets (e.g. flash drive, iPod, external HDD)
```

## Reference

See `references/usbstor-example.md` for a sample USBStor device list.

## Companions

- `server-device-history`

Server-admin thin companions exist and should be preferred when the context is operational rather than purely forensic. When updating this skill, verify compatibility with all companions and other callers; split only if needs have diverged, with a convergence plan.
