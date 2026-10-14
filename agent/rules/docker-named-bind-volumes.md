---
paths:
  - "**/docker-compose*.yaml"
  - "**/docker-compose*.yml"
  - "**/compose.yaml"
  - "**/compose.yml"
---

# Docker Compose named bind volumes

Persistent app data uses a **named volume with a bind-mount driver**. Short-syntax host binds are for sockets and `/etc/localtime` only.

```yaml
services:
  app:
    volumes:
      - app-data:/container/path

volumes:
  app-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ${HOME}/.var/appname
```

Create the host `device` directory before `compose up` (the bind driver requires it). `${HOME}` is the compose process owner: as root that is `/root/.var/<stack>`, not `/home/<user>/.var/<stack>`.

For new compose stacks under `${HOME}/docker/<stack>`:

| Kind | Host path |
|------|-----------|
| State / config / sqlite | `${HOME}/.var/<stack>` |
| Durable data | `${HOME}/.local/share/<stack>` |
| Logs / cache | `${HOME}/.cache/<stack>` |

Feedback: `{MEMORY_ROOT}/feedback-docker-named-bind-volumes.md`
