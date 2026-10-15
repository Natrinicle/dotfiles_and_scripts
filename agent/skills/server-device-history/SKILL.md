---
name: server-device-history
description: "Server companion to usb-device-history. Extend USBStor enumeration to Linux udev/journal, SetupAPI, and broader removable-media or unexpected-device detection on servers and admin hosts."
type: knowledge
lifecycle: active
---

# Server Device History

Thin companion to `usb-device-history`.

## Core reuse

Apply `usb-device-history` for Windows USBStor extraction and the `USB_DEVICES` block.

## Server additions

- Linux: `journalctl -k`, `/var/log/messages`, udev db (`/run/udev/data`), `lsblk`, `dmesg` USB/SCSI attach events.
- Windows Server: USBStor + SetupAPI.dev.log.
- Focus: unexpected storage, HID, or network devices on servers that should be headless.
- Serial correlation still useful for inventory.

## Output

Same `USB_DEVICES` block; add `source: usbstor|udev|journal|setupapi`.

## Upstream note

Device description + serial format is shared.
