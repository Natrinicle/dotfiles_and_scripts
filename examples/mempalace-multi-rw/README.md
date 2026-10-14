# MemPalace multi-reader / multi-writer hub

Replicate a **shared HTTP hub** so several agents (Claude, Grok, CLI, hooks)
read and write the same palace at the same time.

`install.sh --agent` copies the `prefer-mempalace` **rule** (lookup/write
policy). It does **not** install these units. Copy this directory onto the
machine that will run the hub.

Chroma is a **single writer**. Concurrent mines need a multi-process backend
(**Qdrant** or pgvector), `MEMPALACE_MCP_ALLOW_PEER_WRITER=1`, one HTTP hub,
and the write daemon.

## Layout

| Piece | Role |
|-------|------|
| Compose **Qdrant only** | Vector store on `127.0.0.1:6333` |
| systemd `mempalace-mcp-http` | GPU (or CPU) HTTP MCP on `:8765` |
| systemd `mempalace-daemon` | Serial mine queue (`mempalace mine --daemon`) |
| Agent clients | Grok: HTTP `/mcp`. Claude: `mempalace-mcp --palace` (forwards to the hub) |

Do **not** run the compose MCP sidecar beside the systemd hub. The sidecar is
profile `sidecar` for copy/verify only.

## 1. Directories

Named bind volumes (see rule `docker-named-bind-volumes`):

```bash
mkdir -p \
  "${HOME}/.local/share/mempalace/qdrant" \
  "${HOME}/.var/mempalace/palace" \
  "${HOME}/.var/mempalace/container-home" \
  "${HOME}/.mempalace/staging"
```

| Host path | Use |
|-----------|-----|
| `${HOME}/.local/share/mempalace/qdrant` | Qdrant storage |
| `${HOME}/.var/mempalace/palace` | Palace marker, KG sqlite, dest of a Chroma copy |
| `${HOME}/.var/mempalace/container-home` | Sidecar `$HOME` if you ever start profile `sidecar` |
| `${HOME}/.mempalace/staging` | Mine staging (hub `PrivateTmp=true` hides host `/tmp`) |

## 2. Qdrant

```bash
STACK="${HOME}/docker/mempalace"
mkdir -p "$STACK"
cp docker-compose.yaml .env.example "$STACK/"
cd "$STACK"
cp .env.example .env
chmod 600 .env
# set MEMPALACE_MCP_HTTP_TOKEN in .env (sidecar only; systemd hub mints its own)
docker compose up -d
curl -sf http://127.0.0.1:6333/readyz
```

Pin the Qdrant tag (`qdrant/qdrant:v1.19.1` here). `user: "0:0"` is for
**rootless** Docker so the bind owner is the compose user. On a rootful
engine, drop `user:` and chown the bind directories instead.

## 3. Palace path is an identity

Qdrant collection names hash `PalaceRef.id`, which hashes the **palace path
string**. systemd `--palace`, CLI `palace_path`, Claude `--palace`, and a
sidecar `--palace` must be the **same expanded string** (for example
`/home/{user}/.var/mempalace/palace`). `~/…` vs `/home/{user}/…` are
different ids.

The host hub talks to `http://127.0.0.1:6333`. The sidecar (if used) talks to
`http://qdrant:6333`. `qdrant_backend.json` stores **one** URL. Leave the
marker on `http://127.0.0.1:6333` while the systemd hub is live. A leftover
`http://qdrant:6333` marker makes host mines fail with a remote-target mismatch.

## 4. Optional: copy an existing Chroma palace

Skip this on a new palace.

1. Stop the hub if it still holds the live Chroma directory.
2. Snapshot that directory (do not copy from a palace the hub still has open).
3. Copy stored MiniLM vectors into Qdrant (no re-mine):

```bash
export SRC_PALACE="${HOME}/.var/mempalace/chroma-snapshot"
export DEST_PALACE="${HOME}/.var/mempalace/palace"
export MEMPALACE_QDRANT_URL="http://127.0.0.1:6333"
# Marker URL the *host* hub will use:
export QDRANT_MARKER_URL="http://127.0.0.1:6333"
python3 copy-chroma-to-qdrant.py
```

MCP/diary drawers have no source files. Re-mine cannot rebuild them. Keep the
snapshot until search-verify on Qdrant looks right.

## 5. systemd hub + write daemon

Units in `systemd/` use `%h` (the user home). They do not hard-code a login.

```bash
./install-units.sh
# After Qdrant is up:
systemctl --user enable --now mempalace-mcp-http.service mempalace-daemon.service
curl -sf http://127.0.0.1:8765/healthz   # ok
```

`mempalace daemon start` **without** `--foreground` exits 0 if a daemon is
already running. The unit is `Type=simple` and **must** use
`daemon start --foreground`, or systemd hits start-limit.

`MEMPALACE_MCP_IDLE_HOURS=0` on the 24/7 hub. The default 8h idle-exit is for
leftover stdio MCP processes; idle-exit plus `Restart=always` tears down the
user cgroup.

Optional GPU MiniLM (`onnxruntime-gpu` in the pipx venv): copy
`cuda-cudnn.conf.example` to
`~/.config/systemd/user/mempalace-mcp-http.service.d/cuda-cudnn.conf` and set
`LD_LIBRARY_PATH` to that venv’s `nvidia/cudnn/lib` (needs `libcudnn.so.9`).
The published `ghcr.io/mempalace/mempalace` image is CPU-only; keep GPU on the
host hub.

## 6. CLI write routing

Merge into `~/.mempalace/config.json` (absolute `palace_path`, same string as
`--palace`):

```json
{
  "palace_path": "/home/{user}/.var/mempalace/palace",
  "backend": "qdrant",
  "qdrant_url": "http://127.0.0.1:6333",
  "write_routing": {
    "default": "prefer",
    "cli": "prefer",
    "hooks": "prefer"
  }
}
```

`mempalace mine --daemon` **waits** on the job by default. Hooks that must not
block use the daemon submit API with `wait=False`. Do not pass `--direct`
beside the hub.

## 7. Agent clients

**Grok** — HTTP, so the session never loads the palace in-process:

```toml
[mcp_servers.mempalace]
url = "http://127.0.0.1:8765/mcp"
bearer_token_file = "~/.mempalace/server/{palace_id_prefix}/token"
```

The hub mints the token on first `mempalace serve` (mode 0600). Restart Grok
after changing `config.toml`. A leftover stdio `mempalace-mcp` in an old
session attaches in-process (“WITHOUT its shared hub”) and can CUBLAS-fail
searches while the daemon is mining.

**Claude** — stdio forwarder (see `clients/claude-mcp.json.example`):
`mempalace-mcp --palace {PALACE}` with `MEMPALACE_BACKEND=qdrant` and
`MEMPALACE_MCP_ALLOW_PEER_WRITER=1`. `{PALACE}` is the same absolute path as
systemd.

`/healthz` is unauthenticated. `/mcp` and `/statusz` need `Authorization: Bearer`.

## 8. Confirm multi-RW

While `mempalace daemon status` shows a **running** mine:

1. `mempalace search "…"` (or HTTP `mempalace_search`) still returns hits
2. HTTP `mempalace_kg_add` and `mempalace_add_drawer` succeed
3. `/statusz` → `palace.backend` is `qdrant`; `writer.read_only`,
   `peer_writer_read_only`, and `peer_writer_lock_failed` are all false

Hub writes do not wait on the daemon worker. Extra CUDA CLI processes beside
the hub+daemon can fail with CUBLAS allocation errors; search through `:8765`
or `CUDA_VISIBLE_DEVICES=""`.

Priority on the daemon queue is **DESC then `created_at`**. A high-priority
mine runs after the in-flight job, ahead of a pile of session `convos` mines.

## Do not

- Point the hub at a Chroma palace while the daemon is running
- Run compose profile `sidecar` on `:8775` next to systemd `:8765`
- Open a second in-process palace (`--direct`, extra container MCP, stale
  stdio MCP without `--palace` forwarding)
- Copy `prefer-mempalace` into domain-only toolkits (`remote_codes`,
  court-case-monitor). That rule lives in this general pack only
- Print or commit the bearer token or compose `.env`

## Files in this directory

| Path | What |
|------|------|
| `docker-compose.yaml` | Qdrant + optional CPU sidecar |
| `.env.example` | Sidecar token placeholder |
| `systemd/*.service` | User hub + write daemon |
| `systemd/mempalace-mcp-http.service.d/` | Qdrant backend, idle-hours, optional CUDA |
| `install-units.sh` | Copy units into `~/.config/systemd/user/` |
| `clients/` | Grok HTTP + Claude stdio snippets |
| `copy-chroma-to-qdrant.py` | Optional vector copy, no re-mine |
