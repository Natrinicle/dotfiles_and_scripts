---
name: decompile-mobile-app
description: >
  Use when an APK, XAPK, or IPA must be unpacked to recover BLE GATT, HTTP, or
  serial framing; when a uni-app, Flutter, or native Android/iOS binary is the
  only source. Not for MCU firmware blobs or Flipper .ir files.
---

# Decompile mobile app

**REQUIRED BACKGROUND:** **reverse-engineering-protocols** (classify first).

Parent `scripts/unpack_artifact.py` already printed the kind. Follow that kind.

| Kind | Look here first | jadx |
|------|-----------------|------|
| uni-app | `assets/apps/__UNI__*/www/app-service.js` | Only if a `.so` holds framing |
| Flutter | `lib/**/libapp.so` | Yes, isolate |
| Native Android | `classes*.dex` | jadx |
| IPA | `Payload/*.app` | same split |

HTTP: host/path/JSON keys in that tree, then a proxy. Do not commit tokens.

Prove BLE/serial with a live tap. Copy the app's unit conversion. One BLE
central: unbind the phone first.

When the parent pack is a BLE/WiFi remote catalog (`remote_codes` or
equivalent), also harvest **supported-device detection** and **preset
catalogs** in the same unpack (see reverse-engineering-protocols).

Unpack and jadx/strings walks are a **child** (`dump-harvest`, T2, effort
**high** — skill `model-router`). Do not dump the APK tree into the parent.

Paths: `reverse-engineering-protocols` → `references/artifact-kinds.md`.
