# Model Routing

Always-on spawn and pin policy. Taxonomy, routing table, cost, and skill audits: skill `model-router`. Parent vs local for the interactive session: skill `skill-router`. Spend gate (USD, tokens, wall-clock, context-window, **parent compaction** on spawn): rule `expected-value` / skill `expected-value`. These are one policy split by load cost — do not collapse the skill into this rule.

Prefer **local models (Ollama)** for light work. Keep **remote/cloud** models for orchestration, multi-step coding, and high-stakes judgment.

Parent compaction is billed **in+out at parent rates**. When parent-do would grow that window, spawn a cheap/local child (skill `expected-value`). The child's compact is the child's rate (`$0` local). Search/answer backends (web_search, Firecrawl, vendor Search APIs) are tools, not taxonomy tiers.

## Spawn local first (automatic)

Every spawn uses this rule plus skill `model-router` (task id → tier →
model → effort). Pinned light types omit `model` so `[subagents.models]`
applies (`explore`, `code-explorer`, `conversation-analyzer`,
`plugin-validator`, roles `local-extract` / `local-search` →
`ollama-gemma4`). Unpinned / dump-harvest / protocol-recover children
load the skill and pass the table's `model`.

Spawn `explore` or `code-explorer` when the next work is **source-tree**
search (healthy T0 pin):

- Code exploration, “how does X work”, architecture / call-graph mapping
- Nested discovery across locations (search → sub-search → sub-sub-search)
- Extract/summarize from a large file on disk

A dump walk (jadx, `libapp.so`, firmware, unpack dirs, many commands in
one blob tree) is **`dump-harvest` (T2)**, not T0 explore. Protocol
frames + encoder pack is **`protocol-recover` (T2)**. See skill
`model-router`. Spawn those **before** a parent discovery loop (rule
`subagents-first`).

A single search command, or one command piped into grep, stays on the
parent.

Tool-free T0 text **already in context** → skill-router direct Ollama `/api/generate` (no explore child).

**Ollama overloaded:** T0 may fall back to the **lowest upstream** tier
(T1). Claude: Haiku. Grok: cheapest cloud slug in the spawn enum that is
not the xhigh parent session id and not another Ollama/LiteLLM-local id
(`grok-4.7`, default effort **high**). Retry HTTP 503 once, then T1 is
allowed. A slow VRAM load is not overload.

**Escalate once** if the local result is empty, malformed, shallow, or misses files that exist: redo at the next model-router tier (dump-harvest stays T2, not Haiku). Keep the local result when it is usable.

Skip the child when the user named 1–2 exact files, the next step is one
search command or a command piped into grep, or the work is a single
helper, MCP / browser / review / judgment call the parent is already
doing.

Offload: rule **subagents-first**. Spawn for software install that includes
config and service files, **nested discovery loops**, decompile, large
extract, multi-file implementation. Parent summarizes and verifies. Model
+ effort: this rule / skill `model-router`. Hook `prefer-spawn-search`
**denies** a nested discovery loop; one search command stays on the
parent. One large unit → `spawn_subagent`.
Several units that do not share a window → skill **agent-graphs**.

## Grok CLI short-circuit (saves remote tokens)

On Grok Build / Grok CLI:

1. **Do not** read the full model-router skill or the entire routing table before every **pinned T0** spawn. The pin is the route when Ollama is healthy.
2. Light subagent types are already pinned in `~/.grok/config.toml` → `[subagents.models]` to `ollama-gemma4`. Spawn them; the pin is the route.
3. Open skill `model-router` and `{MEMORY_ROOT}/model-routing-table.md` when the task is unpinned: dump-harvest, protocol-recover, Claude Agent `model`, adding/changing a tier, auditing cost, or Ollama overload fallback.
4. Parent stays on cloud (`grok-build`) for planning, MCP, implementation, and synthesis.

Pins match the **exact** `subagent_type` (`explore`, `code-explorer`,
`local-search`, …). Plugin ids such as `feature-dev:code-explorer` are **not**
rewritten to `ollama-gemma4`. Grok's gemma4 model entry is a **16K** window;
plugin explore inject is ~24K, so that pin overflows before the first tool.
On Grok Build, unknown-path search: omit `subagent_type` (cloud
general-purpose) or use the plugin explorer type with **no** local model.
PreToolUse hook `spawn-subagent-local-pin` pins native explore-class names
only. Explicit cloud `model` is left in place. Reviewers and
`general-purpose` are untouched. Restart the session after hook edits.

## Claude Code / Agent tool path

Before dispatching a subagent via the Agent tool (Claude Code), consult the routing table at `~/.claude/memory/model-routing-table.md` for the task's assigned model. Use the `model` parameter on the Agent tool call when the platform supports it.

## Shared rules (both platforms)

- Validate subagent output (empty, shallow, wrong structure). Critical task fail → next model tier.
- Log dispatches to `~/.firecrawl/model-routing/usage-log.jsonl` when practical (task_id, model, validation).
- When creating or editing skills, decompose so T0/T1 phases can stay local.
- **T0 default:** Ollama `gemma4` (direct `localhost:11434` or Grok model id `ollama-gemma4`). Claude T0 curl falls back to haiku if Ollama is down **or overloaded**. Grok: T0 pin when healthy; on overload, lowest upstream cloud slug (`grok-4.7` default **high**), not parent xhigh, not `litellm-gemma4`. First load into VRAM can take minutes (CLIP warmup); use a 600s client timeout and `keep_alive=-1`. Preload the T0 tag before a burst of local calls. HTTP 503 is the queue — retry once, then T1 lowest-upstream fallback is **allowed**. A slow VRAM load is not overload. Details: skill `model-router`.

## What stays remote (do not pin to 8B local)

- `plan`, `general-purpose`, code reviewers, architecture critics, adversarial/style judgment, PII risk judgment, multi-file implementation agents
- Dump harvest / jadx / firmware strings / protocol recover (`dump-harvest`, `protocol-recover`) — T2, effort **high**. Not Haiku, not gemma4, not Fable, not parent **xhigh**.

## Decision models (System One) vs chat T0

Closed yes/no, enum, or rubric over text is a **decision-model** (DMM: Jev / Nimble / Kev) shape, not a chat-essay shape. **Current T0 remains `gemma4`** until a DMM is installed and eval’d (this host Ollama 0.32.1; Nimble needs 0.35+). Do not use a DMM for `decision-judge` advocates or other T3 prose. Palace: `Jev Nimble Kev System One gemma4` (wing `personal`).

## Employer parent (WYNet Claude)

Catalog ids `wynet-claude` (`claude-sonnet-5-5`) and `wynet-claude-opus` (`claude-opus-5-5`) talk to `https://api.anthropic.com/v1` with `api_backend=messages`. Auth is `env_http_headers` `x-api-key` ← `WYNET_ANTHROPIC_API_KEY` (fail closed if unset). Relic KV `secret/wynet/anthropic` field `api_key`; helper `--fetch-key` writes `~/.config/employer-parent-model/secrets.env` (mode 600). Do not use `env_key` (Bearer). Do not put the key in `config.toml`.

**In scope:** cwd under `~/repos/wynet` or `~/repos/WYNet`; employer product AI/infra (AICP, Relic, cells, dogfood tenant). **Out of scope:** personal laptop stacks, home repos, cabin LAN.

Default `EMPLOYER_CLAUDE_AUTH=claudeai`: Claude Code uses Claude.ai subscription sign-in (`employer-claude --login`). Direnv unsets API keys and does not set `GROK_DEFAULT_MODEL` to an Anthropic API slug. Grok stays on the default parent. Do not `/model wynet-claude` in claudeai mode — that path is an API key and bills per token.

`EMPLOYER_CLAUDE_AUTH=api-key`: legacy Console path. Grok cannot swap the live parent on cwd. New sessions: direnv `GROK_DEFAULT_MODEL` in those trees, `employer-grok`, or `grok -m wynet-claude`. In an open session, tell the user to `/model wynet-claude` when the prompt is in scope. Fail closed if the key env is unset. Keep `[subagents.models]` T0 on `ollama-gemma4`. `spawn_subagent` cannot pass a custom Anthropic id; general-purpose children inherit the parent.

Claude Code: keep `~/.claude/settings.json` on LiteLLM for personal work. Employer trees use `employer-claude` / `claude-wynet`. claudeai mode synthesizes `--settings` with `forceLoginMethod=claudeai` and no `apiKeyHelper`. api-key mode uses the overlay (empty `ANTHROPIC_AUTH_TOKEN`, POSIX `apiKeyHelper` `employer-anthropic-api-key`, official `ANTHROPIC_BASE_URL`). Direnv prepends `~/.config/employer-parent-model/bin` so `claude` in a hooked employer tree is the wrapper. Nested git checkouts without direnv still need the wrapper (umbrella `.claude/settings.local.json` does not apply). Do not put the key in settings JSON.

Helper: `employer-parent-model`. Table: `{MEMORY_ROOT}/model-routing-table.md`. Palace: `wynet-claude GROK_DEFAULT_MODEL WYNET_ANTHROPIC_API_KEY 2026-11-07` / `employer-claude apiKeyHelper AUTH_TOKEN 2026-11-07` / `EMPLOYER_CLAUDE_AUTH claudeai 2026-11-18`.
