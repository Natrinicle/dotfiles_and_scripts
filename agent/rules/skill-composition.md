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
   live BLE, APK unpack, firmware blob, timestamp clues, bandwidth likelihood,
   timestomp detection, execution evidence, shell items, SRUM, shell history,
   CVE/KEV scan, persistence indicators, credential access, log clearing, etc.),
   call it. Do not copy its procedure.
2. **Split if broad.** One skill must not be “identify any protocol” or “do all
   forensics.” Dispatcher skills stay a table + **REQUIRED** sub-skill names.
   Procedures live in the sub-skill.
3. **Compiled app or firmware blob** → **reverse-engineering-protocols**, then
   **decompile-mobile-app** (APK/XAPK/IPA, uni-app/Flutter/native) or
   **decompile-firmware** (MCU `.bin`/`.hex`, on-device ELF, UART/I2C/SPI).
   When **reverse-engineer-anything** (REA MCP) is connected, use it for
   shipped binaries, packages, JS/Electron, Android, firmware images, and
   runtime observation. Do not fold REA procedures into the unpack dispatcher.
4. **IR capture** → **flipper-ir-library** for parsed/basic NEC and pack layout;
   **decoding-ir-protocols** for raw / state / advanced (Carrier-style). Do not
   fold IR decode into decompile skills.
5. New sub-skill only when a kind has its own unpack path or bit-map rules.
   Do not add a sub-skill that only restates the parent.
6. **Find vs patch vs skeptic** → **find-patch-loop**, then **bug-finder**,
   **bug-skeptic**, **bug-patcher**. Do not grow **check-work** into a hunt
   loop. Session-complete verification stays **check-work**.
7. **Forensic vs server-admin** → core skills (file-timestamp-clues,
   download-bandwidth-likelihood, identical-folder-copy-indicators,
   timestomp-detection, execution-evidence, shell-item-activity,
   srum-network-volume, shell-history-integrity, cve-kev-scan,
   persistence-indicators, credential-access-indicators,
   log-clearing-indicators, etc.) plus
   thin companions (server-timestamp-clues, server-timestomp-detection,
   server-execution-evidence, powershell-history-integrity,
   server-persistence-indicators, server-credential-access-indicators,
   server-log-clearing-indicators, …).
   Companions apply the core first and only add environment-specific artifacts.
   When updating a core, check all listed companions and other callers for
   compatibility; split only if needs have diverged, with a convergence note.
8. **CUPS custom backend / KDE persist** → **cups-custom-backend**. Label
   CUPS packaging (Nelko / Aimotech) → **cups-label-printer** (REQUIRED
   cups-custom-backend; lives in a specialized catalog pack). Do not grow
   reverse-engineering-protocols.
9. **Research claims vs a cited source** → **claim-source-check**. Do not
   grow **independent-checker** into the swarm/vault procedure. Bug hunt
   stays **find-patch-loop**.
10. **Graph vs loop vs hunt** → **agent-graphs** for the shape of work
    (splitter, isolated workers, code nodes, blast-radius gate, learning
    edge). Inner produce-check-correct is **loop-until-green**. Bug hunt
    stays **find-patch-loop**. Session-complete stays **check-work**.
    Landing stays **ask-before-remote-actions**. Do not grow
    **subagents-first** into graph topology.
11. **Reconstruct vs unpack vs REA MCP** → **clean-room-reconstruct** for
    SPEC.md → rebuild → oracle → retry. Unpack classification stays
    **reverse-engineering-protocols**. Shipped-artifact analysis stays
    **reverse-engineer-anything**. Inner retry is **loop-until-green**.
    Do not dump a studio catalog of GitHub URLs into any of those skills.
12. **Repeatable host procedure vs thought loop** → **prefer-helper-scripts**.
    If pinentry, dialogs, or session dbus can be a shell script, write or
    call that helper. Do not grow a skill into a dump of one-off compound
    commands.

Own hardware / own copy only. Do not commit APKs, blobs, or secrets.
