---
paths:
  - "**"
---

# Public API authentication

No API interface may be reachable from the public Internet unless the user
**named** it public **and** it is gated by strong authentication.

This includes REST, MCP, gRPC, GraphQL, WebSocket, SSE, and any HTTP path
that accepts methods or returns application data — including through a
reverse proxy, tunnel, CDN, load balancer, or hostname pin.

## Strong authentication

Acceptable: Bearer or API key checked at the edge **and** the origin, mTLS,
OAuth/OIDC, or equivalent mutual proof. Empty credentials, `Basic` without a
secret, and "trusted network" alone are not enough once the path is on WAN.

TLS, a reverse proxy, a Host header, an IP allowlist of `0.0.0.0/0`, and
flags such as `--allow-insecure` or `--no-auth` are **not** authentication.

Unauthenticated `/healthz`, `/metrics`, `/debug`, OpenAPI, or `tools/list`
on a public or WAN-proxied URL is a blocker when the body can identify the
service or dump config. A boolean liveness probe may stay public only if
the user named it and the body has no secrets.

## Evidence

Before calling an API public or "done":

1. An unauthenticated request from an untrusted path returns 401/403 (not 200).
2. The listen table and proxy config match that gate.
3. Access logs do not store `Authorization` or cookies.

Do not publish a loopback-only API through a proxy without the same gate.
Do not add a public hostname or tunnel to an unauthenticated origin.

## Related

- **system-security** — WAN bind of control plane, SSH, dashboards
- **security** — app authn/z, secrets
