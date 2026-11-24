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
    SPEC.md → rebuild → oracle → retry (four rules; spec writer ≠
    implementer). Optional engine: Craft Anything (clean-room default /
    Deep). Unpack classification stays **reverse-engineering-protocols**.
    Shipped-artifact analysis stays **reverse-engineer-anything**. Inner
    retry is **loop-until-green**. Do not dump a studio catalog of GitHub
    URLs (Craft app suite included) into any of those skills.
12. **Repeatable host procedure vs thought loop** → **prefer-helper-scripts**.
    If pinentry, dialogs, session dbus, or any **more-than-one-command** host
    sequence can be a shell script, write or call that helper. One-shot pipes
    (`ss | grep PORT`) stay on the parent. Multiple greps that look reusable
    (router diagnostics) become a helper. Do not spawn a child only to run
    that sequence. Do not grow a skill into a dump of one-off compound
    commands.
13. **Security hunt vs hunt-and-patch** → **security-audit** (coverage-ledger,
    findings.json, no patcher) vs **find-patch-loop** (bug-finder /
    bug-skeptic / bug-patcher). Do not grow security-audit into a patcher.
    Do not grow find-patch-loop into an audit coverage ledger.
14. **Design-doc goldfish review vs session-complete / claim-grade** →
    **egm-*** plus `agent/agents` personas vs **independent-checker** /
    **check-work** / **speckit**. A Goldfish is a fresh-context design
    review. Session-complete verification stays check-work. Claim vs source
    stays claim-source-check.
15. **Obsidian Flavored Markdown / Bases / Canvas / CLI vs vault plugin** →
    **obsidian-markdown**, **obsidian-bases**, **json-canvas**,
    **obsidian-cli**, **defuddle**, **knap**. Do not grow a vault-host
    plugin into OFM syntax.
16. **Interview / grill the user vs grade the stated ask** →
    **interview-me** / **grilling** vs **grade-stated-ask**. Grilling
    gathers requirements. Grade-stated-ask quotes the user's words and
    grades that ask.
17. **Web platform CSS/JS vs Chrome extensions vs Motion Canvas scenes** →
    **modern-web-guidance** for HTML/CSS/client JS (guides + `npx`
    search/retrieve; offline `guides/**/<id>.md`). **chrome-extensions**
    for Manifest V3 extension builds and Chrome Web Store listing files.
    **motion-canvas** for TypeScript generator vector animations
    (`makeScene2D`, Vite editor). CSS view transitions stay on
    modern-web-guidance. Labeled system-flow GIFs stay on
    **system-flow-viz**. Print PDFs stay on **illustrated-brochure**.
    Unlabeled generated video stays on **imagine**. Code-drawn
    JS/Python frame video, one-file three.js games, and floor-plan
    walkthroughs stay on **code-drawn-media**. Do not vendor
    `@motion-canvas/ffmpeg` (GPLv3) into a toolkit.
18. **Desktop window vs webpage vs thread evidence** → **screenshot**
    dispatcher, then **screenshot-window** (KWin CaptureWindow, no
    activate, `/tmp/agent-screenshots`) or **screenshot-webpage**
    (Chrome DevTools). GitHub/Slack thread evidence stays
    **thread-screenshots**. OCR of already-captured images stays
    **screenshot-writing-style**. Do not grow browser-testing into
    KWin window capture.
19. **Agent-only nested Plasma / preview / isolated Chromium / teardown**
    → **ephemeral-display** (`ephemeral-display` on PATH). Capture still
    **screenshot-window** or **screenshot-webpage**. Host plasmashell
    stays up. Do not grow screenshot into session lifecycle.
20. **One-file code-drawn game / film / 3D walkthrough** →
    **code-drawn-media** (from-scratch three.js HTML, JS/Python frames,
    Playwright + ffmpeg, floor-plan tour). Unlabeled generated clips stay
    on **imagine**. Motion Canvas scenes stay on **motion-canvas**.
    Labeled system GIFs stay on **system-flow-viz**. Do not grow
    **vibe-pm** into this media path.
21. **Landing / icon / logo / footer / motion galleries before generating
    UI** → **design-inspiration**. Aesthetic identity stays on
    **frontend-design**. Classic/desktop reskin stays on
    **classic-ui-reskin**. Do not grow frontend-design into a URL dump.
22. **Dead code vs readability vs footprint** → **shrink-anything** for
    unused code, files, dependencies, and assets, with the project's own
    tests as the gate and byte-for-byte undo. Readability without deleting
    behavior stays on **code-simplification**. RAM / binary / runtime-weight
    cuts after it works stay on host **footprint-trimmer** (not in this
    pack). Do not grow those skills to cover test-gated dead-code deletion.
    Do not edit tests to make a cut pass.

Own hardware / own copy only. Do not commit APKs, blobs, or secrets.
