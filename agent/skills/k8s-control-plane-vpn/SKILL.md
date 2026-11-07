---
name: k8s-control-plane-vpn
description: >
  Restrict Kubernetes API, kubelet, etcd, and other control-plane ports
  off the WAN. Overlay VPN is optional ("if using a VPN"); air-gapped
  cells still DROP the public NIC. Use when kubeadm, k3s, rke2, closing
  WAN :6443/:10250, cell bootstrap, or a new k8s node. Complements
  system-security.
---

# Kubernetes control plane — off the WAN

Control-plane ports stay off the public internet. That holds for an
overlay VPN **and** for air-gapped cells. A working kubeconfig from
the install session is not proof the API is private.

Load **system-security**. Mutate (ACL, certs, iptables, cloud firewall)
only when the user names that landing step.

## Ports

| Port | What | WAN |
|------|------|-----|
| 6443 | kube-apiserver | operator path only (VPN overlay, admin LAN, or console) |
| 10250 | kubelet | closed on WAN (and on the overlay unless named) |
| 2379 / 2380 | etcd | loopback / overlay. kubeadm still listens on the advertise IP — DROP it on the WAN nic |
| 10257 / 10259 | controller-manager / scheduler | loopback |
| 10256 | kube-proxy healthz | closed on WAN (unauthenticated JSON) |
| 2375 / 2376 | Docker API | loopback |
| hostPorts | OTLP / agent health / metrics from `ss` + `kubectl` hostPort | closed on WAN |

Public `:80` / `:443` (named edge) and break-glass SSH stay a separate
decision. Do not piggyback those onto this close.

## Sequence (every new node)

1. **Operator path exists** before any WAN DROP.
   - **If using a VPN:** overlay up on the node (`tag:server` or the
     cell's equivalent). Ping from an operator device. ACL allows
     operator → API `:6443` only. Do not open `tag:server:*`.
   - **If air-gapped:** admin LAN, console, or IPMI is the path.
     There is no overlay ACL.
2. **If using a VPN — extra SANs** for the overlay IP and DNS name.
   Keep existing names. Do **not** change `--advertise-address` or
   `--bind-address`.
   `kubeadm certs renew apiserver` copies SANs from the existing cert.
   `kubeadm init phase certs apiserver` skips if `apiserver.crt`/`key`
   already exist. Move those two files aside (the running process keeps
   the old cert in memory), then:
   `kubeadm init phase certs apiserver --apiserver-advertise-address=<node-ip> --apiserver-cert-extra-sans=<overlay-ip>,<overlay-dns>,<overlay-fqdn>`
   Reload with `crictl stop` on the apiserver container. Do **not** mv
   the static-pod manifest out of `/etc/kubernetes/manifests` (that can
   leave `:6443` down).
3. **Prove** `kubectl` on the operator path with TLS verify **before**
   any WAN DROP. Keep a break-glass SSH or console session open.
4. **Host DROP** on the public NIC only. Take a listen table
   (`ss -lntp`) and `kubectl` hostPort/hostNetwork list first.
   Host-network listeners (`:6443`, `:10250`, etcd on the advertise
   IP, kube-proxy `:10256`, unused rpcbind `:111`) DROP on filter
   **INPUT** `-i <wan-iface>`. CNI hostPorts (OTLP `:4317`/`:4318`,
   agent health/metrics) DNAT in PREROUTING then **FORWARD**; Calico
   may ACCEPT there. DROP those in `raw PREROUTING` **and** `FORWARD`
   `-i <wan-iface>` as well.
   Example INPUT: `iptables -I INPUT 1 -i <wan-iface> -p tcp -m multiport --dports 6443,10250,2379,2380,10256,111 -j DROP`
   Persist (oneshot unit plus a timer if Calico Felix `ChainInsertMode`
   puts `cali-*` back at position 1). Do not `iptables -F`. Do not
   enable empty cloud default-deny. Do not apply a ufw role that only
   allows 22/80/443.
5. **Untrusted-path evidence**: from a host **not** on the operator
   path, `:6443/version` is not 200; `:10250`, etcd, kube-proxy
   healthz, and hostPorts are unreachable. Listen table may still
   show `*:6443` (bind `0.0.0.0` + NIC DROP is expected).

## Do not

- Bind apiserver only to a VPN / overlay IP (breaks `127.0.0.1` and
  node InternalIP)
- Change `--advertise-address` to a VPN IP (kubelet→API outage)
- Enable a provider Network Firewall empty
- Punch WAN `:6443` for a home IPv4
- Skip WAN DROP because the cell is air-gapped
- Declare the cell built on YAML intent

## Hooks

Native PreToolUse `control-plane-exposure.py` denies `kubeadm init` /
`join`, k3s/rke2 server, `ufw allow` / `iptables ACCEPT` / `0.0.0.0/0`
on those ports. `kubeadm init phase certs` and DROP/REJECT stay
allowed. Escape only after the user names it:
`SYSTEM_SECURITY_ALLOW_WAN_CONTROL_PLANE=1`.

Hookify (project `.claude/hookify.*.local.md`) is a second deny for
Claude Bash/Write. The native hook covers Grok `run_terminal_command`
/ `write`.

## Related

`system-security`, `public-api-auth`, `k8s-ops-readonly`,
`ask-before-remote-actions`
