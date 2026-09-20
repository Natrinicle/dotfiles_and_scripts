# Artifact kinds

Output of `scripts/unpack_artifact.py` is the index. This file is only the
paths that script cannot print as a sentence.

## Android (APK / XAPK)

XAPK is a zip of split APKs. Protocol code is almost always in the base APK,
not `config.arm64_v8a.apk`.

**uni-app / DCloud:** package id often `uni.UNICxxxxx`. Tree:

```
assets/apps/__UNI__<id>/www/app-service.js   # minified Vue logic
assets/apps/__UNI__<id>/www/manifest.json
```

Search that JS for `writeBLE`, `181a`/`ffe0`/`fff0`, `uni.request`, CRC
tables. Native BLE is the uni runtime; framing is in JS.

**Flutter:** `lib/<abi>/libapp.so` + `libflutter.so`. Protocol is not in
DEX.

**Play/HTTP:** `okhttp3`, `Retrofit`, `Uri.parse`, `baseUrl`. Confirm with
a proxy; the APK may pin or wrap the body.

## Apple IPA

Zip; `Payload/*.app`. Same split: JS bundle vs native vs Flutter.

## ELF / PE / shared objects

`strings -n 8` first (UART baud, I2C addresses, AT commands, URL prefixes).
Then symbols. Ghidra when you need the byte-packer, not to “see the C”.

## Microcontroller blob

Identify ISA (ARM Cortex vector table at 0, RISC-V, 8051). Find the UART
or I2C driver, then the caller that builds frames. Do not lift the whole
firmware into a client — lift the frame and CRC only.

## After unpack

Live-prove, then store the protocol beside the device (BLE spec under
`~/.ble_mcp/specs/`, `encode_*.py` in a codes pack, or a small serial
script). Do not keep the APK in git.
