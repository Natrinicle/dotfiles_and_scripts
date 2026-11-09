---
name: reverse-engineering-protocols
description: >
  Use when source is unavailable and a compiled app or firmware blob must be
  classified before recovering how it talks (BLE, UART, I2C, HTTP, serial);
  when writing the recovered protocol README next to a device; or when a
  BLE/WiFi app's device-detection list or named presets belong in that
  encoder. Not for Flipper photo packaging or decoding an already-captured
  raw .ir.
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

When the **REA** MCP server is connected, load **reverse-engineer-anything**
for shipped-artifact analysis (native, JS/Electron, Android, firmware,
runtime). This dispatcher stays for `unpack_artifact.py` then the decompile
sub-skills. Clean-room reconstruct (SPEC.md → oracle → retry) is
**clean-room-reconstruct**.

## Classify

Run `scripts/unpack_artifact.py <path>`. Hash, kind, likely sources.

| Kind | Sub-skill |
|------|-----------|
| uni-app, Flutter, native Android, IPA | **decompile-mobile-app** |
| MCU blob, ELF/PE on a chip, UART/I2C in firmware | **decompile-firmware** |

Then prove the wire in that sub-skill (live tap, CRC on TX and RX, copy the
app's unit conversion). Write the protocol next to the device.

## Spawn (rule `subagents-first` + skill `model-router`)

jadx, `strings`, firmware walks, and other discovery loops run in a
**child**, not the parent window. Task ids `dump-harvest` and
`protocol-recover` are **T2**, effort **high** (skill `model-router`).
Not parent xhigh, not Fable, not Haiku/gemma4. Parent summarizes and
verifies. Ollama-overload fallback is T1 for T0 pins only — dump harvest
stays T2.

For BLE/WiFi apps (APK/IPA/uni-app/Flutter) packed into a remote catalog,
also harvest **supported device connection types** and **presets** by
default into the encoder plus unit README. Unpack stays in
**decompile-mobile-app**; MCU blobs stay **decompile-firmware**.

## Device README

Each device or family has its own directory. The unit README covers that
unit: identification, GATT/UART, frames, helper. Name another product
when it shares this unit's wire, UUID, advertisement, or a sibling path
in this family (USB vs BLE vs LAN).

When the source is a BLE or WiFi app, put these on the encoder and the
unit README. Harvest how the app actually detects/pairs, not a store-listing
guess.

**Supported device connection types:**

- advertised names / prefixes / regexes
- scan UUID / GATT service + chars
- manufacturer company id / MAC OUI only if the app filters on them
- WiFi: SSID prefix, SoftAP, UDP/TCP ports, mDNS, cloud vs LAN
- blocklists / feature gates that hide UI for some SKUs

Pack a print-only `devices --list` (and match-if-useful) on the encoder
plus a README table so the pack can talk to every device that app would
accept. Family SKUs that share this unit's wire/UUID/advertisement belong
on that card.

**Presets** — named effects, scenes, factory animations/pictures,
sound-reactive modes, lamp-light catalogs, with wire bytes / opcodes.
Encoder `--list` plus a README table. Mark unrecovered payloads
explicitly.

## Do not

- Guess `FFE0` / `AA55` from a store listing.
- Implement APK and firmware procedures here.
- Decode `.ir` files here.
- Commit APKs, blobs, or secrets. Own copy only.
