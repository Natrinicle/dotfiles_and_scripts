# Model Routing

Always-on spawn and pin policy. Taxonomy, routing table, cost, and skill
audits: skill `model-router`. Parent vs local for the interactive session:
skill `skill-router`. Spend gate (USD, tokens, wall-clock, context-window, **parent compaction**
on spawn): rule `expected-value` / skill `expected-value`. These are one
policy split by load cost — do not collapse the skill into this rule.

Prefer **local models (Ollama)** for light work. Keep **remote/cloud** models
for orchestration, multi-step coding, and high-stakes judgment.

Parent compaction is billed in+out at parent rates. When parent-do would
grow that window, spawn a cheap/local child (skill `expected-value`). The
child's compact is the child's rate (`$0` local). Search/answer backends
(web_search, Firecrawl, vendor Search APIs) are tools, not taxonomy tiers.

## Spawn local first (automatic)

Every spawn uses this rule plus skill `model-router` (task id → tier →
model → effort). Pinned light types omit `model` so host T0 pins apply.
Unpinned / dump-harvest / protocol-recover children load the skill and
pass the table's `model`.

Spawn `explore` or `code-explorer` when the next work is **source-tree**
search (healthy T0 pin):

- Code exploration, “how does X work”, architecture / call-graph mapping
- File search over **multiple locations** or an unknown forest
- Extract/summarize from a large file on disk

A dump walk (jadx, unpacked app/firmware, many commands in one blob tree)
is **`dump-harvest` (T2)**, not T0 explore. Protocol frames + encoder pack
is **`protocol-recover` (T2)**. Spawn those before a parent discovery loop
(rule `subagents-first`).

A single `rg` / `grep` of one tree, or one command piped into grep, stays
on the parent.

Tool-free T0 text **already in context** → a short local generate (no explore
child). See skill `skill-router`.

**Ollama overloaded:** T0 may fall back to the **lowest upstream** tier
(T1). Claude: Haiku. Grok: cheapest cloud slug in the spawn enum that is
not the xhigh parent session id and not another local/Ollama id. Retry
HTTP 503 once, then T1 is allowed. A slow VRAM load is not overload.

**Escalate once** if the local result is empty, malformed, shallow, or misses
files that exist: redo at the next model-router tier (dump-harvest stays T2,
not Haiku). Keep the local result when it is usable.

Skip the child when the user named 1–2 exact files, the next step is one
`rg`/`grep` of one tree or a command piped into grep, or the work is a
single helper, MCP / browser / review / judgment call the parent is
already doing.

Offload: rule **subagents-first**. Spawn for software install that includes
config and service files, multi-location search, **discovery loops**,
decompile, large extract, multi-file implementation. Parent summarizes
and verifies. Model + effort: this rule / skill `model-router`. Hook
`prefer-spawn-search` **denies** forest and multi-location search; a single
`rg` of one tree, or a command piped into grep, stays on the parent. One
large unit → `spawn_subagent`.
Several units that do not share a window → skill **agent-graphs**.

## Grok CLI short-circuit

On Grok Build / Grok CLI:

1. Do **not** re-read the full model-router skill or routing table before every
   **pinned T0** spawn. The pin is the route when Ollama is healthy.
2. Light subagent types are already pinned in the host config. Spawn them;
   the pin is the route.
3. Load skill `model-router` and `{MEMORY_ROOT}/model-routing-table.md` when
   the task is unpinned: dump-harvest, protocol-recover, Claude Agent `model`,
   adding/changing a tier, auditing cost, or Ollama overload fallback.
4. Parent stays on a capable model for planning, MCP, implementation, and
   synthesis.

Pins match the **exact** `subagent_type` (`explore`, `code-explorer`,
`local-search`, …). Plugin ids such as `feature-dev:code-explorer` are **not**
rewritten to the host T0 local id. Grok's gemma4 model entry is a **16K**
window; plugin explore inject is ~24K, so that pin overflows before the first
tool. On Grok Build, unknown-path search: omit `subagent_type` (cloud
general-purpose) or use the plugin explorer type with **no** local model.
PreToolUse hook `spawn-subagent-local-pin` pins native explore-class names
only. Explicit cloud `model` is left in place. Reviewers and
`general-purpose` are untouched. Restart the session after hook edits.

## Claude Code / Agent tool path

Before dispatching a subagent via the Agent tool, consult
`{MEMORY_ROOT}/model-routing-table.md` for the task's assigned model. Use the
`model` parameter when the platform supports it.

## Shared rules (both platforms)

- Validate subagent output (empty, shallow, wrong structure). Critical task
  fail → next model tier.
- Log dispatches when practical (task_id, model, validation).
- When creating or editing skills, decompose so T0/T1 phases can stay local.
- **T0 default:** local Ollama. Fall back to the **lowest upstream** tier
  (T1 / Haiku, or the cheapest cloud slug on Grok) if Ollama is down **or
  overloaded**. Retry HTTP 503 once, then T1 is allowed. A slow VRAM load
  is not overload. Do not fall back to Fable, Opus, or parent xhigh.
  First load into VRAM can take minutes; use a 600s client timeout and
  `keep_alive=-1`. Preload the T0 tag before a burst of local calls.
  Details: skill `model-router`.

## What stays remote (do not pin to 8B local)

- `plan`, `general-purpose`, code reviewers, architecture critics,
  adversarial/style judgment, PII risk judgment, multi-file implementation
  agents
- Dump harvest / jadx / firmware strings / protocol recover
  (`dump-harvest`, `protocol-recover`) — T2, effort **high**. Not Haiku,
  not local 8B, not Fable, not parent **xhigh**.

## Decision models (System One) vs chat T0

Closed yes/no, enum, or rubric over text is a **decision-model** (DMM: Jev /
Nimble / Kev) shape, not a chat-essay shape. Keep current T0 on the local chat
model until a DMM is installed and eval'd (Nimble needs Ollama ≥0.35). Do not
use a DMM for `decision-judge` advocates or other T3 prose. Details:
palace `Jev Nimble Kev System One gemma4` (wing `personal`).

## Employer-tree parent (optional)

When the host defines an employer parent (`[model.*]` plus
`employer-parent-model` config), use that parent for employer trees and
employer-named AI/infra work only. Personal work stays on the default parent.
T0 explore pins stay local.

Grok cannot swap the live parent mid-session. New sessions: direnv
`GROK_DEFAULT_MODEL`, `employer-grok`, or `grok -m <slug>`. In an open
session, tell the user to `/model <slug>`. Fail closed if the key env is
unset. Do not put secrets in config.toml; Anthropic Messages needs
`env_http_headers` for `x-api-key` (not `env_key` Bearer). `--fetch-key`
writes `secrets.env` (mode 600) from Vault path names in config.env.

Claude Code: keep user settings on the personal gateway. Employer trees
use `employer-claude` (`--settings` overlay: empty `ANTHROPIC_AUTH_TOKEN`,
POSIX `apiKeyHelper` `employer-anthropic-api-key`, official
`ANTHROPIC_BASE_URL`). Do not put the key in settings JSON. `--direnv`
prepends `${XDG_CONFIG_HOME}/employer-parent-model/bin` when that dir
has a `claude` shim so `claude` in a hooked employer tree is the
wrapper. Nested git checkouts without direnv still need `employer-claude`.
Config example: `examples/employer-parent-model.env.example`. Settings
example: `examples/employer-claude-settings.json.example`.
