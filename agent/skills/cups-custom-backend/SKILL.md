---
name: cups-custom-backend
description: Use when KDE print-manager, CUPS custom backends, last-seen discovery, or persistent queues for unknown URI schemes.
---

# CUPS custom backend persist

Keep a **configured CUPS dest** so KDE System Settings → Printers still
shows the queue when the hardware is off. Discovery is a separate list.

MemPalace: `cups-custom-backend` and
`KDE Printers list configured dest last-seen retry-job` (wings `personal`
/ `tools` and `personal` / `hardware`).

Label-printer packaging in a specialized catalog pack also loads
**cups-label-printer**.

## KDE 6.7 print-manager

| Surface | Source | When empty |
|---------|--------|------------|
| Main Printers list | `PrinterModel` → `getPrinters` (configured dests) | No dest in `printers.conf` |
| List title | `printer-info` (lpadmin `-D`), not `printer-name` | — |
| Add Printer | CUPS Get-Devices | Device unseen this boot and no last-seen cache |
| Add Printer connection UI | `FindPrinter.qml` by `device-class`; unknown URI scheme → NotAvailable | Custom scheme (`aimotech`, `nelko`, …) |

Do not treat Add Printer as the queue list. After `lpadmin`, reopen System
Settings. Existing dests expose `device-uri` as text in Printer Settings.

## Persist a dest

```
lpadmin -p QueueName -E -v scheme://AA-BB-CC-DD-EE-FF \
  -m drv:///scheme.drv/model.ppd \
  -D "Human Title" -o printer-error-policy=retry-job
```

- Dest in `printers.conf` is what the KDE list shows while the printer is off.
- `-D` is the list title.
- `retry-job` holds jobs until RFCOMM / the backend is back.
- Setup helper: pass `--mac` while the printer is off (lpadmin group).

## Backend contract

- Install `/usr/lib/cups/backend/<scheme>` mode **0700** root. CUPS ignores a
  world-executable backend. `cupsd` runs it as root; job submitters do not
  need the `bluetooth` group.
- Advertise dash-separated MAC hosts (`scheme://AA-BB-CC-DD-EE-FF`). CUPS 2.4
  `httpSeparateURI` treats colon octets as a port. Parse colon, dash, and
  12-hex; use colon on the RFCOMM socket.
- Last-seen file `/var/cache/cups/<scheme>.devices` (`MAC<TAB>name`). Merge
  after live `bluetoothctl` and `/var/lib/bluetooth`. **Write the cache only
  when `live_seen` is non-empty** so an empty boot does not wipe last-seen.
- Cap ~16 names. Skip placeholder `AA:BB:CC:DD:EE:FF` and deny-list names.
- Get-Devices `device-class` `direct` so KDE Add Printer can finish. Do
  **not** merge existing dests into Get-Devices (duplicate-queue).

## Do not

- Expect KDE to know a custom URI scheme.
- `bluetoothctl pair` for SPP backends that print unpaired.
- Treat BlueZ Connect / HID BLE ads as the print path.
- Invent GATT `FFE0` or send the wrong job language.

## Related

**cups-label-printer** (Bluetooth label catalog). Palace unique phrase
`cups-custom-backend lpadmin retry-job last-seen print-manager list vs Add 2026-10-29`.
