# Model Routing

Prefer **local models (Ollama)** for light work. Keep **remote/cloud** models
for orchestration, multi-step coding, and high-stakes judgment.

## Spawn local first (automatic)

Before a discovery loop on the parent, spawn a pinned light child
(`explore`, `code-explorer`, `local-search`, `local-extract`, and any other
types the host config pins to Ollama). Omit an explicit `model` so the pin
applies.

Spawn `explore` or `code-explorer` when the next work is:

- Code exploration, “how does X work”, architecture / call-graph mapping
- File search over unknown paths (tree grep/glob, “where is X defined”)
- Extract/summarize from a large file on disk

Tool-free T0 text **already in context** → a short local generate (no explore
child). See skill `skill-router`.

**Escalate once** if the local result is empty, malformed, shallow, or misses
files that exist: redo on the parent or `general-purpose`. Keep the local
result when it is usable.

Skip the child when the user named 1–2 exact files, or the work is a write /
install / MCP / browser / review / judgment call.

## Grok CLI short-circuit

On Grok Build / Grok CLI:

1. Do **not** re-read the full model-router skill or routing table before every
   local spawn.
2. Light subagent types are already pinned in the host config. Spawn them;
   the pin is the route.
3. Load `{MEMORY_ROOT}/model-routing-table.md` only when adding/changing a
   tier, auditing cost, or dispatching a Claude Agent-tool call that needs an
   explicit `model`.
4. Parent stays on a capable model for planning, MCP, implementation, and
   synthesis.

## Claude Code / Agent tool path

Before dispatching a subagent via the Agent tool, consult
`{MEMORY_ROOT}/model-routing-table.md` for the task's assigned model. Use the
`model` parameter when the platform supports it.

## Shared rules (both platforms)

- Validate subagent output (empty, shallow, wrong structure). Critical task
  fail → next model tier.
- Log dispatches when practical (task_id, model, validation).
- When creating or editing skills, decompose so T0/T1 phases can stay local.
- **T0 default:** local Ollama. Fall back to a small cloud model only if
  Ollama is down (Claude/T0 curl path); Grok local pins fail closed if Ollama
  is down.

## What stays remote (do not pin to 8B local)

- `plan`, `general-purpose`, code reviewers, architecture critics,
  adversarial/style judgment, PII risk judgment, multi-file implementation
  agents
