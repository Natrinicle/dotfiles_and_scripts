# Method

## Frame split

Flipper `data:` is mark, space, mark, space, … in microseconds. A value
**> 10000** (10 ms) is an inter-frame gap, not a bit.

Typical HVAC raw line:

- 3 × (header + 32–40 data bits + stop mark) with ~20 ms gaps
- or 6 × that (two messages)

Header is often ~8.0–8.5 ms mark + ~4.1–4.2 ms space (Carrier AC40-class).
Bit mark ~500–560 µs. Zero space ~500 µs. One space ~1500–1540 µs. Frequency
in the file is usually 38000, duty 0.33.

IRremoteESP8266 names (`CARRIER_AC`, `CARRIER_AC40`) are **timing families**,
not a promise of bit count. Match timings, then count bits from the capture.
A 36-bit payload with invert-middle is not `sendCarrierAC40()` (40 bits, no
invert).

## Bit extract

Skip the two header samples. Then pairs `(mark, space)`: `space > 1000` → 1.
Stop when the next space is a gap or the list ends on a lone mark (stop bit).

Print:

- nbits
- hex MSB, 8-bit groups, last group may be a nibble
- invert check vs the next frame
- leftover samples

Group bits 0–7, 8–15, … as bytes. HVAC snapshots often keep a constant device
id in the first 16 bits.

## Field map

Make a spreadsheet (or print) of every unique first-frame payload.

| Control | What to hold still | What should move |
|---------|--------------------|------------------|
| Setpoint | mode, fan | a compact field, often one byte |
| Mode | setpoint, fan | another byte / nibble |
| Fan | setpoint, mode | nibble or two bits |
| Power off | — | may overlay several bits, not a single flag |
| Off timer | climate snapshot + extra bit | **second** 36-bit word |

If Cool 90 and Dry 90 share the setpoint byte, that byte is independent of
mode **at that temp**. That does not prove every temp. Missing cells stay
missing.

Trailer nibbles (`C` vs `E`) can track mode *and* odd setpoints. Copy the
captured trailer when splicing.

## Two-packet messages

`nframes == 6` and frames 0–2 look like a climate snapshot: frames 3–5 are a
second triple. Diff packet 2 across 1H vs 12H (or similar). A 4-bit field that
bit-reverses to the hour count is enough to fill 2–11, still marked synthesized.

ON TIMER that never appears in the `.ir` did not transmit.

## Encode script

When more than a handful of fills are needed, put `encode_<model>.py` next to
the `.ir`:

- constants: header, bit mark, zero/one space, gap, stop, nbits
- `triple_frame(payload)` = data, `NOT data`, data
- two-packet helper when timers exist
- `--list-known` prints learned payloads only
- synthesized emits must say so in the Flipper `#` comment

Learned `data:` lines stay the Flipper samples (jitter included). Synthesized
lines may use nominal timings.

## Worked pattern (Carrier-class cassette)

Not every remote. Use as a checklist for invert-middle 36-bit HVAC:

- Device id constant (`B3 35` in that capture)
- Byte 2 setpoint / power / timer-enable mix
- Byte 3 high nibble = mode+fan; low nibble stayed `F`
- Trailer nibble not a checksum of the bytes
- Off timer = snapshot with one extra bit, then `B3 35 7X F1 0` with `X` =
  bit-reversed hour

Copy the method (diff, invert check, two-packet, mark fills). Do not copy those
hex values onto a different model.
