---
name: srum-network-volume
description: "Extract per-application bytes sent and received from the Windows SRUM database (SRUDB.dat) to quantify network transfers. Use when assessing possible data exfiltration; chain after bandwidth or execution skills."
type: knowledge
lifecycle: active
---

# SRUM Network Volume

Quantify network usage per application and user from the System Resource Usage Monitor database.

## Core facts

- Location: `C:\Windows\System32\sru\SRUDB.dat` (ESE database).
- Network Usage table records `BytesSent` / `BytesRecvd` per app, user SID, and interface/profile in roughly hourly buckets.
- Retention typically 30–60 days. Survives process deletion.
- Does not record destination IPs or URLs — combine with proxy, DNS, or firewall logs.
- High outbound volume from uncommon tools (rclone, curl, archive utilities) is a classic signal.

## Analysis Steps

1. Parse Network Usage records for the relevant window.
2. Sum bytes sent/received by application and user.
3. Flag outliers relative to normal system usage.
4. Note the network profile (SSID or interface) when available.

## Output Format (for chaining)

```
SRUM_VOLUME
window: YYYY-MM-DD .. YYYY-MM-DD
top_senders:
  - app: "..."
    user_sid: "..."
    bytes_sent: N
    bytes_recv: N
notes: short bullets
```

## Companions

Windows-only. On Linux servers use auditd, `ss`, or external flow data instead.

When updating, keep the bytes and SID fields stable for chaining.
