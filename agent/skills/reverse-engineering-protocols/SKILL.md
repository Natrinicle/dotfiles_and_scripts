---
name: reverse-engineering-protocols
description: >
  Use when source is unavailable and a compiled app or firmware blob must be
  classified before recovering how it talks (BLE, UART, I2C, HTTP, serial).
  Not for Flipper photo packaging or decoding an already-captured raw .ir.
---

# Reverse-engineering protocols

Dispatcher only. Classify the artifact, then **load the sub-skill**. Do not
unpack every kind in this file.

**REQUIRED SUB-SKILL:** **decompile-mobile-app** for APK/XAPK/IPA.
**REQUIRED SUB-SKILL:** **decompile-firmware** for MCU `.bin`/`.hex` or
on-device ELF.

IR is not this tree: **flipper-ir-library** (parsed/basic + pack),
**decoding-ir-protocols** (raw / state / Carrier). Live BLE after GATT is
known: BLE MCP.

## Classify

Run `scripts/unpack_artifact.py <path>`. Hash, kind, likely sources.

| Kind | Sub-skill |
|------|-----------|
| uni-app, Flutter, native Android, IPA | **decompile-mobile-app** |
| MCU blob, ELF/PE on a chip, UART/I2C in firmware | **decompile-firmware** |

Then prove the wire in that sub-skill (live tap, CRC on TX and RX, copy the
app’s unit conversion). Write the protocol next to the device.

## Do not

- Guess `FFE0` / `AA55` from a store listing.
- Implement APK and firmware procedures here.
- Decode `.ir` files here.
- Commit APKs, blobs, or secrets. Own copy only.
