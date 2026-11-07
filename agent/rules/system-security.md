---
paths:
  - "**"
---

# System security

Apply when building, installing, exposing, reviewing, or declaring a
**system** done: host, VM, container, compose stack, Kubernetes/Helm cell,
reverse proxy, firewall, or cloud security group. Also apply when writing or
reviewing code that will run on those systems.

A working kubeconfig from the install session is not proof the API is private.

## Public exposure (blockers)

These stay off the public internet (`0.0.0.0/0`, WAN, unauthenticated HTTP)
unless the user **named** that service as public **and** auth + TLS are in
place:

- Kubernetes API (`:6443`), kubelet (`:10250`), etcd (`:2379` / `:2380`)
- kube-scheduler (`:10259`), kube-controller-manager (`:10257`)
- SSH, IPMI / iDRAC / iLO, Docker / containerd sockets (`:2375` / `:2376`)
- Unauthenticated dashboards, metrics, registries, debug ports
- Unauthenticated APIs (REST, MCP, gRPC, WebSocket, SSE) — see **public-api-auth**
- NodePort, hostPort, hostNetwork, LoadBalancer, or Ingress without auth

**Kubernetes / new nodes:** control-plane ports are **VPN / loopback /
cluster overlay only**. Close WAN on the public NIC (`iptables`/`nft` DROP
or equivalent SG). Do not rebind `--advertise-address` or `--bind-address`
to the VPN IP. Extra SANs + a working VPN kubeconfig **before** any WAN
DROP. Procedure: skill **k8s-control-plane-vpn**.

**Evidence before "it's built" or "it's up":**

1. Listen table on public/WAN addresses (`ss`, cloud SG, host firewall).
2. Bind flags (`--bind-address`, `advertiseAddress`, `insecure-port`).
3. An untrusted **non-VPN** path cannot reach the control plane. If that
   check is impossible from here, the exposure is **unverified**.

Unverified is not private. Do not close the task on YAML intent alone.

## Enforcement

Native PreToolUse hook `{AGENT_HOME}/hooks/control-plane-exposure.py`
denies `kubeadm init`/`join`, k3s/rke2 server, and opening those ports
(`ufw allow`, `iptables ACCEPT`, `0.0.0.0/0`). DROP/REJECT and
`kubeadm init phase certs` stay allowed. UserPromptSubmit injects this
gate on spin-up prompts. Hookify rules under project
`.claude/hookify.*.local.md` are a second deny. Escape only after the
user names it: `SYSTEM_SECURITY_ALLOW_WAN_CONTROL_PLANE=1`.

## Scraped vulnerability catalogs

Refresh CISA KEV / NVD / GainSec, then read
`{MEMORY_ROOT}/vulnerability-patterns.md`. Use **cve-catalog** when that
skill is installed.

- Review CWE classes from that catalog (injection, XSS, authz, SSRF, path
  traversal, deserialization, missing auth). This is not CVE-ID matching of
  source.
- Dependencies: `trivy fs` (see **security**).
- Do not write exploits or attack payloads.

## Code and config

Follow **security** (injection, XSS, authn/z, secrets) and **code-quality**
(lint / format). Kubernetes/Helm also **helm-k8s** (pin image tags, non-root).
Least privilege. Secrets in a manager or env, not git. TLS on anything named
public.

## Related

- **k8s-control-plane-vpn** — sequence for API/kubelet VPN-only
- **public-api-auth** — public REST/MCP/gRPC/WebSocket need strong auth; a reverse proxy is not auth
- **security** — app / API / IaC scanners
- **cve-catalog** — KEV / NVD / GainSec refresh + CWE review
- **iac-plan-analysis** — `0.0.0.0/0` on plans
- **k8s-ops-readonly** when installed — inspect a cluster; mutate only when named
