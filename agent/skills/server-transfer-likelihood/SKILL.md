---
name: server-transfer-likelihood
description: "Server companion to download-bandwidth-likelihood. Reuse core rate logic with modern link speeds for rsync, scp, object-storage, and backup transfers. Use when assessing whether a large data movement on a server was a network transfer or a local copy."
type: knowledge
lifecycle: active
---

# Server Transfer Likelihood

Thin companion to `download-bandwidth-likelihood`. Apply the core calculation first.

## Core reuse

Follow `download-bandwidth-likelihood` for the bytes/time → required rate method and the structured `BANDWIDTH_LIKELIHOOD` block.

## Server rate table (sustained)

| Path                  | Typical sustained | 100 GB time   | 1 TB time    |
|-----------------------|-------------------|---------------|--------------|
| 1 Gbps                | ~100 MB/s         | ~17 min       | ~3 h         |
| 10 Gbps               | ~1 GB/s           | ~2 min        | ~17 min      |
| 40/100 Gbps / fabric  | 3–10+ GB/s        | seconds–1 min | minutes      |
| Cloud egress (varies) | 1–10 Gbps         | check region  | check region |
| rsync over WAN        | often << line rate| highly variable |              |

- Local copy (same host, NVMe, or SAN) can exceed 1–5 GB/s and finish multi-TB in minutes.
- A required rate above the known NIC or inter-site link, plus a tight birth-time cluster, favors local copy.

## Output

Same `BANDWIDTH_LIKELIHOOD` block; add `path_type: local|lan|wan|cloud` when known.

## Upstream note

Core rate formula and block format must stay stable for this companion.
