---
name: n8n-workflow
description: Generate n8n workflow JSON, import it over the local API, and open the clickable canvas. Use when building n8n DAGs, webhooks, schedules, Ollama nodes, or a visual workflow UI at n8n.localhost.
---

# n8n Workflow

Generate an importable n8n DAG, POST it to the local instance, and open
`http://n8n.localhost/workflow/<id>` so the user can click the canvas.

Stack: image `docker.n8n.io/n8nio/n8n:2.44.7`, Traefik Host `n8n.localhost`,
named bind `${HOME}/.var/n8n`. Pack example: `examples/n8n/`. Live layout is
often `${HOME}/docker/n8n`. Do not publish host `:5678`. Do not disable user
management.

## First-run gate

1. `curl -sS http://n8n.localhost/healthz` → `{"status":"ok"}`.
2. If `/setup` or owner-create is showing, stop and tell the user to create
   the owner in the browser. Then Settings → n8n API → Create API key.
3. Write the key to `${HOME}/.config/n8n/api.key` (mode 0600). Env
   `N8N_API_KEY` wins when set.

Unauthenticated `/api/v1/*` must 401. `GET /healthz` is the loopback liveness
probe (tiny body, no secrets).

Public API uses `X-N8N-API-KEY`. Internal REST `POST /rest/api-keys` needs
cookie `n8n-auth` plus header `browser-id` matching localStorage key
`n8n-browserId`. The session JWT stores sha256-base64 of that UUID; a random
header returns 401. Prefer the key file once minted. Do not print cookies,
JWT payload, or `rawApiKey`.

## Script

```bash
python3 "${HOME}/.claude/skills/n8n-workflow/scripts/n8n_workflow.py" health
python3 "${HOME}/.claude/skills/n8n-workflow/scripts/n8n_workflow.py" create \
  --template webhook-respond --name "Webhook ping" --open
```

| Template | Canvas |
|----------|--------|
| `webhook-respond` | Webhook → Respond to Webhook (JSON `{ok, ts}`) |
| `schedule-http` | Every 15m → HTTP Request |
| `ollama-chat` | Manual trigger → POST `host.docker.internal:11434/api/chat` (`gemma4:latest`) |

`create` writes JSON under `${HOME}/.var/n8n/generated/`, POSTs
`/api/v1/workflows` with `X-N8N-API-KEY`, optionally `--activate`, then
`xdg-open` the editor URL. Always print the markdown link.

Ollama from a node: `http://host.docker.internal:11434`. Nodes cannot read
host env (`N8N_BLOCK_ENV_ACCESS_IN_NODE`).

## After import

Tell the user the canvas URL. They edit nodes there. Do not dump the full
workflow JSON in chat unless they asked for the file.

## Anti-patterns

- Putting `N8N_ENCRYPTION_KEY` or the API key on argv or in a skill file
- `N8N_USER_MANAGEMENT_DISABLED=true`
- Publishing host `:5678` or binding n8n on `0.0.0.0` without Traefik
- Calling Ollama at `127.0.0.1` from inside the container
