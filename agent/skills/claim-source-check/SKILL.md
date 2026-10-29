---
name: claim-source-check
description: >
  Use when a swarm or researcher produces claims that must be checked against
  a source before saving; claim+source checker, never producer reasoning;
  rewrite on fail; vault only verified pages.
---

# Claim-source check

Split produce from trust. One model does the work. A cheaper one decides
whether the claim is true. That is the line between a swarm and a mess.

**REQUIRED:** always-on rule **claim-source-check**.
**REQUIRED:** **prefer-mempalace** for the vault.
**REQUIRED:** **independent-checker** (producer does not grade itself).

Bug hunt is **find-patch-loop**. This skill is claims vs a cited source.

## Roles

| Role | Job | Must not |
|------|-----|----------|
| Producer | Research, write, extract | Grade own claims; file unverified pages |
| Checker | Verdict on claim + source only | See producer reasoning; invent extra nits |
| Vault | Keep `supported` pages | Store guesses |

## Checker input

Give the checker:

1. The claim (one sentence or a tight bullet).
2. The source text (quote, page, or file).

Do not give the producer’s chain of thought, prompt, or “why I believe this.”
The checker judges evidence, not the argument.

```bash
python3 "${AGENT_HOME}/skills/claim-source-check/scripts/claim_source_check.py" \
  --claim 'The PDF title is Motor Vehicle Title Fee Receipt' \
  --source-file ./page.txt
```

`--source-text` for inline text. Default model is local `gemma4` at
`http://127.0.0.1:11434/v1/chat/completions`. Override with
`CLAIM_SOURCE_MODEL` / `--model`.

## Verdict

| JSON `verdict` | Action |
|----------------|--------|
| `supported` | File the page or claim (MemPalace `add_drawer` / `kg_add`) |
| `contradicted` | Send back to the producer for rewrite |
| `insufficient` | Fetch more source or rewrite; do not save |

`quote` must be a span from the source. Empty quote on `supported` is a fail
→ treat as `insufficient`.

## Swarm

1. Producers run in parallel on disjoint slices.
2. Each claim is checked independently (claim + that claim’s source).
3. Failures rewrite once. Second fail → drop or inbox; do not vault.
4. Only `supported` pages are saved.

Checker spawn: omit `model` so the T0 pin applies (`ollama-gemma4`). Do not
load the routing table to pick the checker.

## Do not

- Pass producer notes into the checker prompt.
- Save because the producer sounded sure.
- Use this skill to rubber-stamp a bug patch (that is **bug-skeptic**).
