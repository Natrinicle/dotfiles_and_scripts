# Model Routing

Always-on spawn and pin policy. Taxonomy, routing table, cost, and skill
audits: skill `model-router`. Parent vs local for the interactive session:
skill `skill-router`. Spend gate (USD, tokens, wall-clock, context-window
on spawn): rule `expected-value` / skill `expected-value`. These are one
policy split by load cost — do not collapse the skill into this rule.

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

Offload: rule **subagents-first**. If a child can finish the step, spawn it (including write / MCP / REA / judgment). Parent summarizes and verifies.

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

Pins match the **exact** `subagent_type`. Plugin ids such as
`feature-dev:code-explorer` miss a `code-explorer` pin. PreToolUse hook
`spawn-subagent-local-pin` rewrites an omitted `model` on explore-class types
to the suffix pin or the host T0 local id, and warns the parent. Explicit
cloud `model` is left in place. Reviewers and `general-purpose` are
untouched. Restart the session after hook edits.

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

## Decision models (System One) vs chat T0

Closed yes/no, enum, or rubric over text is a **decision-model** (DMM: Jev /
Nimble / Kev) shape, not a chat-essay shape. Keep current T0 on the local chat
model until a DMM is installed and eval'd (Nimble needs Ollama ≥0.35). Do not
use a DMM for `decision-judge` advocates or other T3 prose. Details:
palace `Jev Nimble Kev System One gemma4` (wing `personal`).
