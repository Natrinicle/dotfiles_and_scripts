---
name: download-bandwidth-likelihood
description: "Assess whether file size totals and creation-time windows are consistent with internet downloads or local copies. Use when evaluating P2P (LimeWire, etc.) or browser download claims against timestamp clusters and data volume; chain after file-timestamp-clues."
type: knowledge
lifecycle: active
---

# Download Bandwidth Likelihood

Determine if observed Created-time clusters and total bytes are plausible as network downloads. Output a short structured block for chaining into expert-report generation.

## Core Heuristics (circa 2007–2010 consumer broadband)

| Connection     | Typical sustained | 1 GB time     | 5 GB time     |
|----------------|-------------------|---------------|---------------|
| Dial-up 56k    | ~5 KB/s           | ~2.5 days     | ~12 days      |
| DSL/Cable low  | 1–3 Mbps          | 45–90 min     | 4–8 hours     |
| Cable/DSL mid  | 5–10 Mbps         | 15–30 min     | 1–2 hours     |
| High (rare)    | 15–20 Mbps        | 7–12 min      | 35–50 min     |

- LimeWire and similar P2P clients rarely sustained peak rates for multi-GB transfers of many files; overhead, swarm variability, and user pauses are normal.
- A tight Created cluster (<15–20 min) of >3–5 GB of mixed video/image files is far more consistent with a local copy (USB, external HDD, or same-volume folder copy) than with sequential downloads.
- Multiple batches separated by hours can still be copies (user copied in stages).

## Analysis Steps

1. Sum file sizes in the cluster (bytes or GB).
2. Measure wall-clock span from first to last Created timestamp.
3. Compute required sustained rate: bytes / seconds.
4. Compare to era-appropriate broadband (default assumption: residential 1–10 Mbps unless evidence of faster).
5. Note presence of identical folder (same hashes) elsewhere on the volume → prior copy source.
6. If rate exceeds realistic sustained download for the period and environment, conclude “copy far more likely.”

## Output Format (for chaining)

```
BANDWIDTH_LIKELIHOOD
total_size: X GB
time_span: Y min
required_rate: Z Mbps
plausible_as_download: true|false|marginal
preferred_explanation: copy|download|unknown
supporting: short bullets (identical folder, even-second Modified, etc.)
```

## Reference

See `references/bandwidth-examples.md` for the 5 GB / 14 min example and calculation method.

## Companions

- `server-transfer-likelihood`

Server-admin thin companions exist and should be preferred when the context is operational rather than purely forensic. When updating this skill, verify compatibility with all companions and other callers; split only if needs have diverged, with a convergence plan.
