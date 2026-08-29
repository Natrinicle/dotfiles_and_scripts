---
name: decoding-ir-protocols
description: >
  Use when Flipper saved a raw .ir that is not parsed NEC/Samsung/RC5/RC6; when
  decoding AC, HVAC, ceiling cassette, or other state-based infrared remotes;
  when temperature, fan, mode, or timer captures need a bit map; or when writing
  an encode script for custom Flipper IR codes.
---

# Decoding IR protocols

State-based remotes (HVAC, many projectors with long frames) send a **snapshot**
of the whole UI, not “temp up.” Flipper stores them as `type: raw`. Decode the
bit map from captures; do not guess NEC address/command.

Packaging photos and the README tree is **flipper-ir-library**. This skill
stops at: payloads, field map, encode script, which buttons are learned vs
synthesized.

## Workflow

1. Run `scripts/decode_flipper_ir.py` on the `.ir` (or paste). Keep every
   button Flipper named, including unlabeled ones.
2. Split bursts on gaps **> 10 ms**. Count frames. 3 frames with frame1 =
   `NOT frame0` and frame2 = frame0 is the invert-middle triple (common).
   **6 frames** is two triples (timers often do this).
3. Pulse-distance default: space > 1000 µs = 1, else 0; leader is the first
   two samples; a trailing short mark is a stop bit, not a data bit.
4. Build a table: button name → first-frame hex (MSB) → nbits. Confirm the
   inverted middle frame before trusting a row.
5. Diff rows that should change **one** control (same mode, two temps; same
   temp, two fans). A field that flips with the control and stays put otherwise
   is real. Fields that move together may be a checksum — do not splice.
6. Synthesize a code **only** when a field is proven at two or more endpoints
   with an invertible map (example: 4-bit hour, bit-reversed nibble). Put the
   learn in the `.ir` as-is; mark fills as synthesized in comments **and** the
   README. Untested splices stay out of the Flipper file unless the user asks.
7. Write `encode_<device>.py` in the unit folder when building more codes by
   hand would be error-prone (two-packet timers, checksums, 36+ bit state).
8. Hand the payloads to **flipper-ir-library** for `.ir` comments, README, and
   “Flipper cannot send this as parsed NEC.”

Details and the invert/timer patterns: `references/method.md`.

## Do not

- Treat Flipper `protocol: NEC` as the HVAC encoding. Raw 38 kHz + ~8.2/4.1 ms
  header is often Carrier-family pulse-distance, not 32-bit NEC.
- Decode only the first burst of a 6-frame capture. Timers hide in packet 2.
- Collapse unlabeled captures (`On_Cool_Auto` vs `On_Cool_Auto_75`) — they may
  be different setpoints with the same Flipper name.
- Assume trailer nibble `C` vs `E` is only “fan.” Capture it per row.
- Invent Heat/Furnace from a Cool payload. Mode lives in its own field; learn it.
- Claim a checksum without a formula that matches every row.

## After decode

Button names encode **state**: `Cool_75_Auto`, `Furn_45_Auto`, `Off_Timer_3H`.
Not `Temp_up`.

ON TIMER with no IR: document “emits nothing on this remote.” Do not fake it.
