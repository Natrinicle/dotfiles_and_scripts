# n8n (local)

Clickable workflow UI at <http://n8n.localhost/> through Traefik on host `:80`.
Image `docker.n8n.io/n8nio/n8n:2.44.7`. Named bind `${HOME}/.var/n8n`.
Compose `user: "0:0"` so rootless Docker can write that bind (image
`USER=node` is container uid 1000 → host 101000). `HOME=/home/node` and
`N8N_USER_FOLDER=/home/node` (parent of `.n8n`) so sqlite lands on the
bind at `/home/node/.n8n`, not container `/root/.n8n` or a nested
`/home/node/.n8n/.n8n`.

`install.sh` does not start this stack. Copy this directory to
`${HOME}/docker/n8n` (or another compose project) and bring it up yourself.

## Bring up

```bash
install -d -m 0755 "${HOME}/.var/n8n"
install -d -m 0755 "${HOME}/docker/n8n"
cp docker-compose.yaml "${HOME}/docker/n8n/"
cp .env.example "${HOME}/docker/n8n/.env"
chmod 600 "${HOME}/docker/n8n/.env"
# replace N8N_ENCRYPTION_KEY in .env with secrets.token_urlsafe(32)
cd "${HOME}/docker/n8n"
docker compose up -d
```

First browser visit creates the owner account. Keep user management on.

## API key (after owner setup)

1. Open <http://n8n.localhost/> and sign in.
2. Settings → n8n API → Create API key.
3. Save the key to `${HOME}/.config/n8n/api.key` (mode 0600).

The `n8n-workflow` skill POSTs `/api/v1/workflows` with `X-N8N-API-KEY` and
opens `/workflow/<id>` in the browser.

Internal REST `POST /rest/api-keys` needs cookie `n8n-auth` plus header
`browser-id` matching localStorage `n8n-browserId` (JWT stores sha256-base64
of that UUID). Prefer the public API key file once minted.

## Ollama from a workflow

Host Ollama should listen on `*:11434`. From the container use
`http://host.docker.internal:11434`. Nodes cannot read host env
(`N8N_BLOCK_ENV_ACCESS_IN_NODE=true`).

## Health

Unauthenticated `GET /healthz` is loopback-only (Traefik Host
`n8n.localhost`). Unauthenticated `/api/v1/*` must 401.
