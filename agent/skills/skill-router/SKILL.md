---
name: skill-router
description: >
  Route work to local Ollama first when quality allows; keep the interactive
  parent when tools are required. Use when choosing local vs cloud, saving
  tokens, switching to Ollama, deciding whether a task needs MCP/tools, or
  starting code exploration / file search that a local explore child should do.
---

# Skill Router

Keep the interactive parent on a capable cloud model. Push tool-free and light
work to local Ollama so upstream tokens stay low.

Model IDs and subagent pins live in `model-router` and
`{MEMORY_ROOT}/model-routing-table.md`. This skill only decides **parent vs local**.

## Parent stays on cloud

Keep the interactive parent on a capable model for any turn that needs tools.
An 8B Ollama parent does not reliably call native host tools or plugin MCP.

Use the parent for:

- MCP, browser, and other host tools
- Multi-file implementation, code review, architecture, PII/style/adversarial judgment
- Image/video generation and web search
- A local pass that came back empty, malformed, or shallow

## Local first

Use local Ollama when the work is extract / classify / summarize of
**already-in-context** text, or a pinned light subagent. The always-on
`model-routing` rule requires spawning `explore` / `code-explorer` for code
exploration and file search over unknown paths — do that before a parent
grep/read loop.

| Path | When |
|------|------|
| Direct Ollama `/api/generate` | Tool-free T0 text. Short prompt, cap `num_predict`. |
| Spawn `explore` / `code-explorer` / `local-search` / `local-extract` | Host config pins these to local Ollama. Skip re-reading the routing table. Omit `model`. |
| Persona `local-brief` | When the parent will re-ingest a long child reply |

Direct generate pattern (same as `model-router`):

```bash
curl -s http://localhost:11434/api/generate \
  -d "$(python3 -c "import json; print(json.dumps({
    'model':'gemma4','prompt':PROMPT,'stream':False,
    'options':{'temperature':0.1,'num_predict':256}}))")" \
  | python3 -c "import json,sys; print(json.load(sys.stdin).get('response',''))"
```

## Mixed turns

Parent gathers with tools. Local synthesizes or extracts from that result.

## Escalation

Empty, malformed, shallow, or missing-files local output → one redo on the
parent (or `general-purpose`). Keep the local result when it is usable. Grok
local pins have no automatic small-cloud fallback; Claude T0 curl does.

## Anti-patterns

- Switching the interactive parent to Ollama for a tool-using task
- Spawning `explore` for tool-free T0 text (instruction-injection tax)
- Parent running a 3+ step grep/read discovery loop that `explore` /
  `code-explorer` should have done
- Pinning `plan`, `general-purpose`, or reviewers to 8B local
