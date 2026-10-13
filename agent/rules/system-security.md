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
- SSH, IPMI / iDRAC / iLO, Docker / containerd sockets
- Unauthenticated dashboards, metrics, registries, debug ports
- NodePort, hostPort, hostNetwork, LoadBalancer, or Ingress without auth

**Evidence before "it's built" or "it's up":**

1. Listen table on public/WAN addresses (`ss`, cloud SG, host firewall).
2. Bind flags (`--bind-address`, `advertiseAddress`, `insecure-port`).
3. An untrusted path cannot reach the control plane. If that check is
   impossible from here, the exposure is **unverified**.

Unverified is not private. Do not close the task on YAML intent alone.

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

- **security** — app / API / IaC scanners
- **cve-catalog** — KEV / NVD / GainSec refresh + CWE review
- **iac-plan-analysis** — `0.0.0.0/0` on plans
- **k8s-ops-readonly** when installed — inspect a cluster; mutate only when named
