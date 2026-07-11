---
name: model-router
description: >
  Map subagent tasks to local vs cloud models by difficulty and cost; trust-then-verify
  with escalation. T0 uses Ollama when available.
---

# Model Router

Skills declare a **task id**; this skill (or the host routing table) maps it to a tier.

## Tiers (intent)

| Tier | Role |
|------|------|
| T0 Local | Structured extract, simple parse, commit-scan-like tasks — Ollama when healthy |
| T1 Cheap cloud | Extraction when local quality fails |
| T2 Mid | Categorization, rule-following analysis |
| T3 Strong | Friction judgment, subtle language, architecture critique |

Read `{MEMORY_ROOT}/model-routing-table.md` when assigning new tasks or auditing cost.
On Grok, respect config pins for light subagents — do not re-read the whole table
before every local spawn.

## Trust then verify

1. Run at the cheapest plausible tier.  
2. Validate shape/quality (non-empty, parseable, not obviously wrong).  
3. **Critical** tasks: escalate immediately on fail.  
4. **Non-critical:** accept with warning; bump tier next time.  

**T0 → T1 silent fallback:** if Ollama is down, model missing, or response empty,
retry on a small cloud model without drama. Local is best-effort.

Escalation path: T0 → T1 → T2 → T3. Log outcomes when practical.

## What stays expensive

Reviews, adversarial judgment, PII risk calls, multi-file implementation, planning.
