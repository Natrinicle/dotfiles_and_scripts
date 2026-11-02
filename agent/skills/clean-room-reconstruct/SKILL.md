---
name: clean-room-reconstruct
description: >
  Use when reconstructing from a shipped binary via SPEC.md, oracles, and
  checks until match; clean-room reconstruct loop; binary to REA to spec
  to rebuild to oracle to retry. Not for unpack classification or REA
  analysis procedures.
---

# Clean-room reconstruct

Sub-skill for **one** reconstruct loop. Write a spec from observed
behavior, rebuild from that spec, then run an oracle until it matches.

**REQUIRED SUB-SKILL:** **reverse-engineer-anything** for shipped-artifact
analysis (REA MCP, Ghidra/IDA providers, Android, runtime).
**REQUIRED SUB-SKILL:** **loop-until-green** for produce / check / correct.
**REQUIRED:** **independent-checker** — the producer does not grade the
oracle.

Unpack classification is **reverse-engineering-protocols**. Graph shape
(several independent claims in parallel) is **agent-graphs**. This skill
is **one unit**.

Studio tool names (Ghidra, jadx, Frida, radare2, …) live in
`references/studio-tools.md`. Procedures stay in the listed skill.

## Flow

```text
binary → REA → SPEC.md → reconstruct → oracle → retry
```

1. Bind the **own-copy** artifact. Ask which path if the user named none.
2. Load **reverse-engineer-anything**. Collect Evidence IDs for the
   claims that will go in the spec. Do not copy original source into the
   rebuild tree.
3. Write `SPEC.md` **before** reconstructing. Claims are observed
   behavior (inputs, outputs, wire, UI), not decompiled text.
4. Write the **oracle** first (skill `loop-until-green`). Preferred
   oracle when advertised: REA `verify_reconstruction` on the typed
   spec. Else a command that can fail (test, schema, golden bytes).
5. Reconstruct from the spec only. Run the oracle.
6. On red: return **this unit** (verdict, reason, evidence, scope).
   Correct the spec or the rebuild. Cap **three** reds, then the plan
   is wrong.

A `verify_reconstruction` pass covers **declared comparable claims**,
not global equivalence. See
`reverse-engineer-anything/references/evidence-workflows.md`.

## SPEC.md

Keep the spec finite and typed. Minimum:

```text
# SPEC
target: <path or sha256>
claims:
- id: <stable id>
  observe: <what the binary did>
  expect: <what the rebuild must match>
oracle: verify_reconstruction | <command>
```

Green is the oracle exit or pass on those claims. "Looks like the
original" is not a check.

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
- Dump a catalog of GitHub URLs into a skill
- Copy recovered source into the rebuild and call it clean-room
- Treat oracle silence or compile-only as green
- Commit APKs, blobs, or secrets. Own copy only
- Land commits or server changes unless the user named that step
