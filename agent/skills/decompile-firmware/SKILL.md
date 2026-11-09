---
name: decompile-firmware
description: >
  Use when a microcontroller .bin/.hex, on-device ELF, or similar blob is the
  only source for UART, I2C, SPI, or other on-the-wire framing. Not for APK/IPA
  unpack or Flipper .ir decode.
---

# Decompile firmware

**REQUIRED BACKGROUND:** **reverse-engineering-protocols** (classify first).

1. `file`, `strings`, vector table / ISA (Cortex, RISC-V, 8051).
2. Find `uart_init` / `i2c_write` / ISR, then the caller that packs frames.
3. Ghidra/r2 for the packer and CRC, not to lift the whole image into a client.
4. Live-prove on the bus if you have the hardware.

Lift **frame + CRC** only. Do not commit the blob.

Strings / Ghidra / r2 walks are a **child** (`dump-harvest`, T2, effort
**high** — skill `model-router`). Do not dump the image into the parent.

Paths: `reverse-engineering-protocols` → `references/artifact-kinds.md`.
