# Correct raw Flipper captures that are parsed protocols

`scripts/correct_parsed_ir.py` rewrites `type: raw` to `type: parsed` only
when the timings are a high-likelihood match for a Flipper discrete protocol
(NEC, NECext, Samsung32) or a bundled button map uniquely identifies a
missing key.

HVAC / Carrier-style 36-bit invert-middle stays raw. Use
**decoding-ir-protocols** for those.

## When Flipper saves NEC as raw

Flipper's NEC decoder uses a tight preamble window (~200 µs). A learn can
miss that window, or the first 32-bit frame can be dropped so only **repeat**
bursts remain:

- Data frame: ~9.0 ms mark, ~4.5 ms space, 32 bits LSB-first, stop mark
- Repeat: ~9.0 ms mark, ~2.25 ms space, stop mark, ~40–110 ms gap

Repeats carry no address or command. Replay of repeat-only raw does not
press the key. The protocol is still NEC.

## Auto-rewrite bar (high likelihood)

Promote raw → parsed when **all** of:

1. After splitting on gaps > 10 ms, at least one frame is a 32-bit payload.
2. Leftover after 32 bits is a single stop mark (~560 µs), not extra bits.
3. Bits decode LSB-first to four bytes `A, ~A?, C, ~C?`.
4. Every payload frame in that button agrees on protocol, address, command.
5. Repeat frames and truncated repeat tails are ignored, not treated as a
   second command.

Protocol pick (same as Flipper's NEC interpret):

| Complements | Protocol | Flipper fields |
|-------------|----------|----------------|
| `A == ~A_inv` and `C == ~C_inv` | NEC | address `A`, command `C` |
| command complement only | NECext | address `A | (A_inv<<8)`, command `C | (C_inv<<8)` |
| neither complement | no rewrite | could be a 32-bit slice of HVAC |

Samsung32: ~4.5 ms / ~4.5 ms header, same 32-bit rules, `protocol: Samsung32`.

Do **not** treat ~8.2 ms / ~4.1 ms + 36 bits as NEC.

## Repeat-only (no payload)

Leave `type: raw`. Tag with `correct_parsed_ir:`. Do not invent a command
byte from button order, odd/even guesses, or a single sibling address.

If the file already has parsed NEC/NECext/Samsung32 at **one** address, that
address is noted in the comment. Re-learn the key for a parsed command.

## Map fill

`references/nec-button-maps.json`. A missing repeat-only key is filled only
when:

- One map matches the file's protocol and address
- Every overlapping parsed button **name** has the same command as the map
- Overlap count ≥ that map's `min_anchors` (default 3)
- No other map also matches
- The raw button did not decode to a conflicting payload

Mark filled keys `correct_parsed_ir: map <id>` in the `.ir` comment and the
unit README.

## Commands

```
correct_parsed_ir.py FILE.ir            # dry-run
correct_parsed_ir.py FILE.ir --write    # rewrite in place
correct_parsed_ir.py DIR --write        # every *.ir under DIR
correct_parsed_ir.py --self-test
```

Run on a new dump **before** decoding HVAC bit maps.
