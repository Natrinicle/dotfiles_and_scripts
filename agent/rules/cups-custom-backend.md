---
paths:
  - "**/cups/**"
  - "**/backend-*"
  - "**/*-setup-printer"
  - "**/printer-driver-*"
  - "**/*.ppd"
  - "**/*.drv"
---

# CUPS custom backend persist

When adding or debugging a **custom CUPS URI scheme** (not ipp/usb/socket):

1. Load skill **cups-custom-backend**.
2. KDE System Settings → Printers **main list** is configured dests
   (`getPrinters`). **Add Printer** is live Get-Devices.
3. Persist with `lpadmin -D … -o printer-error-policy=retry-job`. List title
   is Description (`printer-info`).
4. Backend mode **0700** root. Dash-MAC URI hosts (`scheme://AA-BB-CC-DD-EE-FF`).
5. Last-seen `/var/cache/cups/<scheme>.devices` — write only when live BlueZ
   (bluetoothctl or `/var/lib/bluetooth`) returned names this run.
6. `--mac` on the setup helper adds a dest while the printer is off.
7. Do not merge existing dests into Get-Devices. Do not `bluetoothctl pair`
   for unpaired SPP backends.

Label CUPS trees under `Bluetooth/Printers/**/cups/` also load
**cups-label-printer**.
