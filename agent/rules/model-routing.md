# Model Routing

Prefer **local models** for light extraction and search. Keep **cloud / large** models for orchestration, multi-file coding, and high-stakes judgment.

## Local-first (when configured)
- Pin light subagent types (explore, shallow extractors, simple validators) to a local Ollama (or equivalent) model via host config.
- Do not re-read the full routing table before every local spawn if pins already apply.
- Parent session stays on a capable model for planning and synthesis; push volume work to children.

## When to open the routing table
Load `{MEMORY_ROOT}/model-routing-table.md` only when:
- Assigning or changing task tiers
- Auditing cost or confidence
- Dispatching an Agent-tool call that needs an explicit `model` parameter

## Shared rules
- Validate subagent output (empty, shallow, wrong shape). Escalate model tier on failure for critical tasks.
- Decompose skills so cheap tiers handle volume and expensive tiers handle judgment.
- Keep reviews, architecture critique, security/PII judgment, and multi-file implementation on stronger models.
