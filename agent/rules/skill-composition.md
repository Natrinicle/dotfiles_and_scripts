---
paths:
  - "**/.claude/skills/**"
  - "**/.grok/skills/**"
  - "**/agent/skills/**"
  - "**/SKILL.md"
---

# Prefer sub-skills over one broad skill

When the user asks for a **new skill**, do not grow an existing skill to cover
unrelated media or artifact kinds.

1. **Reuse first.** If another skill already owns a slice (IR pack, raw IR,
   live BLE, APK unpack, firmware blob), call it. Do not copy its procedure.
2. **Split if broad.** One skill must not be “identify any protocol.” Dispatcher
   skills stay a table + **REQUIRED** sub-skill names. Procedures live in the
   sub-skill.
3. **Compiled app or firmware blob** → **reverse-engineering-protocols**, then
   **decompile-mobile-app** (APK/XAPK/IPA, uni-app/Flutter/native) or
   **decompile-firmware** (MCU `.bin`/`.hex`, on-device ELF, UART/I2C/SPI).
4. **IR capture** → **flipper-ir-library** for parsed/basic NEC and pack layout;
   **decoding-ir-protocols** for raw / state / advanced (Carrier-style). Do not
   fold IR decode into decompile skills.
5. New sub-skill only when a kind has its own unpack path or bit-map rules.
   Do not add a sub-skill that only restates the parent.

Own hardware / own copy only. Do not commit APKs, blobs, or secrets.
