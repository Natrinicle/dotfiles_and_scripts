---
name: model-router
description: >
  Map subagent tasks to local vs cloud models by difficulty and cost; trust-then-verify
  with escalation. T0 uses Ollama when available.
---

# Model Router

Always-on spawn/pin policy is rule `model-routing`. **Every spawn uses this
router.** Skip re-reading this skill before every pinned T0 explore when
Ollama is healthy. Load it for dump-harvest, protocol-recover, unpinned
cloud children, and Ollama overload fallback.

Skills declare a **task id**; this skill (or the host routing table) maps it
to the cheapest **viable** tier (missed GATT/opcodes are not viable).

## Tiers (intent)

| Tier | Role |
|------|------|
| T0 Local | Structured extract, simple parse, commit-scan-like tasks — Ollama when healthy. Down or **overloaded** → lowest upstream (T1). Closed yes/no, enum, or score is a **decision-model** (System One) *shape*; keep T0 on the chat model until a DMM is eval'd (palace: `Jev Nimble Kev System One gemma4`). |
| T1 Cheap cloud | Extraction when local quality fails. **Ollama-overload fallback.** Not dump/jadx/protocol harvest. |
| T2 Mid | Categorization, rule-following analysis. **Dump harvest** and protocol recover; effort **high**. Not parent xhigh, not Fable, not Haiku. |
| T3 Strong | Friction judgment, subtle language, architecture critique. Not file/dump search. |

Search/answer backends (web_search, Firecrawl, vendor Search APIs) are
**tools**, not rows in this table. Do not scrape a consumer Ask UI as a
free model. Parent compaction is skill `expected-value` (`C_compact_parent`);
this table is the child's billed work (`$0` local compact).

Read `{MEMORY_ROOT}/model-routing-table.md` when assigning new tasks, auditing
cost, or dispatching dump-harvest / protocol-recover. On Grok, respect config
pins for light subagents when Ollama is healthy — do not re-read the whole
table before every T0 spawn. Dump walks spawn **before** a parent discovery
loop (rule `subagents-first`). Parent vs local: skill `skill-router`.

Task ids: `dump-harvest`, `protocol-recover` — T2, effort **high**. Grok:
pass a cloud id whose default effort is high (not the xhigh parent session
id). Claude: sonnet, effort high.

## Trust then verify

1. Run at the cheapest plausible tier.  
2. Validate shape/quality (non-empty, parseable, not obviously wrong).  
3. **Critical** tasks: escalate immediately on fail.  
4. **Non-critical:** accept with warning; bump tier next time.  

**T0 → T1 silent fallback** if Ollama is down **or overloaded:** `/api/tags`
fails, empty generate, or HTTP 503 after one retry → **lowest upstream**
(T1 Haiku / cheapest Grok cloud slug that is not the xhigh parent and not
another Ollama id). Local is best-effort. A slow VRAM load is not overload —
wait a 600s client timeout. Do not fall back to Fable, Opus, or parent xhigh.

## Ollama VRAM load

The T0 chat model takes a while to copy weights into VRAM (multimodal CLIP
warmup). First `/api/generate` after unload can take minutes; a warm ping is
~1–2s. Treat a slow first byte as load, not as Ollama being down.

- Client timeout **600s** (`curl --max-time 600`, `CLAIM_SOURCE_TIMEOUT`,
  `IDENTITY_SUBAGENT_TIMEOUT`).
- Preload before a burst: `POST /api/generate` with `"keep_alive": -1`.
- `"keep_alive": -1` disables the idle unload timer. The scheduler still
  evicts when `OLLAMA_MAX_LOADED_MODELS` or VRAM requires it.
- HTTP **503** `maximum pending requests exceeded` is the **queue**
  (overload). Retry once; then T1 lowest-upstream fallback is allowed.

The Ollama **server** is often a system unit (`User=ollama`) with
`OLLAMA_KEEP_ALIVE` (default 5m) for clients that omit `keep_alive`. A
user-owned keepalive sidecar can re-pin already-loaded models. Changing the
systemd drop-in needs root.

Escalation path: T0 → T1 → T2 → T3. Log outcomes when practical.

## What stays expensive

Reviews, adversarial judgment, PII risk calls, multi-file implementation,
planning, dump harvest / protocol recover (T2 high; not T3 Fable/xhigh,
not T1 Haiku).
