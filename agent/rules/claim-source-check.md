---
paths:
  - "**"
---

# Claim-source check

Producer and checker are different agents. The checker gets the **claim**
and the **source**, never the producer’s reasoning.

- A cheap/local model (T0 / `gemma4`) judges whether the source supports
  the claim. It does not rewrite the argument.
- Verdict `supported` → save (MemPalace drawer, page, or note).
- `contradicted` or `insufficient` → rewrite. Do not file.
- A missing or failed checker is **unverified**, not a pass.
- Script: skill `claim-source-check` (`claim_source_check.py`).

Bug hunt stays **find-patch-loop**. Session-complete stays **check-work**.
This rule is research/pages/vault claims vs a cited source.
