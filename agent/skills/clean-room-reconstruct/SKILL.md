---
name: clean-room-reconstruct
description: >
  Use when reconstructing from a shipped binary via SPEC.md, oracles, and
  checks until match; clean-room reconstruct loop; binary to REA to spec
  to rebuild to oracle to retry; Craft Anything Study/Build/Check/Ready.
  Not for unpack classification or REA analysis procedures.
---

# Clean-room reconstruct

Sub-skill for **one** reconstruct loop. Write a spec from observed
behavior, rebuild from that spec, then run an oracle until it matches.

**REQUIRED SUB-SKILL:** **reverse-engineer-anything** for shipped-artifact
analysis (REA MCP, Ghidra/IDA providers, Android, runtime).
**REQUIRED SUB-SKILL:** **loop-until-green** for produce / check / correct.
**REQUIRED:** **independent-checker** — the producer does not grade the
oracle. Spec writer and implementer are **different contexts**.

Unpack classification is **reverse-engineering-protocols**. Graph shape
(several independent claims in parallel) is **agent-graphs**. This skill
is **one unit**.

Studio tool names live in `references/studio-tools.md`. Procedures stay
in the listed skill.

## Four rules

A clean-room rebuild copies **behavior**, never the code inside the original.

1. **Observe, never copy.** Black-box the target. Screenshot its own window.
   Do not paste original source, assembly, or wording beyond plain feature
   names into the rebuild tree.
2. **Specs, not sources.** File formats come from public standards and
   observed I/O, never from a competitor's parser or GPL/LGPL code.
3. **Original assets only.** Icons, fonts, templates, and sounds are drawn,
   public-domain, or openly licensed, with a row in an attribution file.
4. **Separate the two jobs.** One context recovers behavior and writes
   `SPEC.md`. A different context implements from the spec alone and never
   opens the original analysis. This split is the clean-room boundary.

Analysis (REA, or Craft Anything Deep on an **own-copy**) may read internals
to write the spec. The implementer must not.

## Flow

```text
binary → REA or Craft Anything → SPEC.md → reconstruct → oracle → retry
```

Optional engine: **Craft Anything** (`craft-anything-cli`; MCP `mcp`;
`rebuild`). Default **clean-room** refuses tools that look inside.
`--deep` is private analysis of an own-copy. Loop: Study → Build → Check
→ Ready. Project folder: `craft.json`, `capture/`, `app/`, `checks/`,
`investigation.cany/`, `inbox/`. Early alpha. Do not dump the Craft app
suite into this skill.

1. Bind the **own-copy** artifact. Ask which path if the user named none.
2. Load **reverse-engineer-anything** (or Craft Anything). Collect Evidence
   IDs for the claims that will go in the spec. Do not copy original source
   into the rebuild tree.
3. Write `SPEC.md` **before** reconstructing. Claims are observed behavior
   (inputs, outputs, wire, UI), not decompiled text. Keep an obligation
   ledger: every recovered behavior needs a passing test.
4. Write the **oracle** first (skill `loop-until-green`). Preferred: REA
   `verify_reconstruction` on the typed spec. Else a command that can fail
   (test, schema, golden bytes, or a behavioral parity harness: same inputs
   to original and rebuild, match rate + divergence list).
5. Reconstruct from the spec only, in a context that never saw the
   decompile. Run the oracle.
6. On red: return **this unit** (verdict, reason, evidence, scope).
   Correct the spec or the rebuild. Cap **three** reds, then the plan
   is wrong.

A `verify_reconstruction` pass covers **declared comparable claims**,
not global equivalence. See
`reverse-engineer-anything/references/evidence-workflows.md`.
"I think it matches" is not evidence.

## SPEC.md

Keep the spec finite and typed. A developer who never saw the binary must
be able to implement from it. Minimum:

```text
# SPEC
target: <path or sha256>
claims:
- id: <stable id>
  observe: <what the binary did>
  expect: <what the rebuild must match>
oracle: verify_reconstruction | <command>
```

Useful headings when the unit is an app: Architecture, Data Model, Public
API, File Formats, Test Cases. Omit addresses, decompile names, and
assembly.

Green is the oracle exit or pass on those claims.

## Return payload

Same shape as **loop-until-green**:

```text
UNIT      <claim id or spec path>
VERDICT   green | red
REASON    <one line>
EVIDENCE  <oracle output, Evidence ID, or path>
SCOPE     <spec claims or rebuild files that may change>
```

## Do not

- Grow **reverse-engineer-anything** or **reverse-engineering-protocols**
  into this loop
- Dump a catalog of GitHub URLs (Craft app suite included)
- Copy recovered source into the rebuild and call it clean-room
- Treat oracle silence or compile-only as green
- Grind multi-layer obfuscation past a per-function budget; bank neighbor
  context and stop
- Commit APKs, blobs, or secrets. Own copy only
- Land commits or server changes unless the user named that step
