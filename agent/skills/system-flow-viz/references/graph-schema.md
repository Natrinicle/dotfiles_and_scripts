# Graph JSON schema

One object. Unknown fields are ignored. Copy `examples/compose-stack.json`.

```json
{
  "title": "Sample compose stack",
  "mode": "combo",
  "chrome": "tui",
  "width": 1200,
  "height": 1500,
  "header": {"host": "sample", "system": "compose stack", "kernel": "Linux"},
  "stages": [
    {"id": "edge", "label": "Edge", "status": "done", "elapsed_s": 0.8, "units": 1, "failed": 0}
  ],
  "nodes": [
    {
      "id": "ingress",
      "label": "proxy",
      "kind": "edge",
      "state": "running",
      "parent": null,
      "description": "TLS terminator",
      "role": "lead",
      "running_s": 1.2
    }
  ],
  "edges": [
    {"from": "ingress", "to": "api", "kind": "talks", "label": "HTTPS", "packets": true, "tone": "o", "volume": "high"}
  ],
  "gates": [{"id": "g1", "label": "before start", "active": true}],
  "log": [{"t": "00:00:01", "tag": "proxy", "tone": "o", "text": "listen :443"}],
  "failures": [{"unit": "db", "reason": "exited with status 1", "lines": ["…"]}],
  "timeline": [
    {"id": "api", "label": "app", "start_s": 0.8, "end_s": 3.2, "state": "running"}
  ],
  "footer": {"done": 1, "running": 1, "waiting": 2, "failed": 0},
  "cli": "render-flow --graph compose-stack.json",
  "keyframes": [
    {"t": 0.0, "nodes": {"api": {"state": "waiting"}}, "gates": ["g1"]},
    {"t": 0.5, "nodes": {"api": {"state": "running"}}, "footer": {"done": 1, "running": 2, "waiting": 1, "failed": 0}}
  ]
}
```

## Fields

| Field | Notes |
|-------|--------|
| `mode` | `tree` / `packet` / `combo` |
| `chrome` | `tui` / `window` |
| `nodes[].parent` | Wait-on parent id, or `null` for a root. Tree nests children under this id |
| `nodes[].state` | `waiting` `running` `done` `failed` `blocked` |
| `nodes[].role` | Packet card color: `lead` `swarm` `local` `advisor` |
| `nodes[].kind` | Free string (`target`, `service`, `edge`, `mount`, …) |
| `edges[].kind` | `talks` draws a packet wire. `depends` is wait-on (tree uses `parent`) |
| `edges[].tone` | `o` `b` `g` `p` `a` `r` |
| `edges[].packets` | `true` to put dots on the wire |
| `edges[].volume` | Expected data on that pipe: `high`/`busy`, `medium`, `low`/`trickle`, or a 0..1 number. Maps to CSS `--dur` (busy ≈ 0.60s, medium 1.60s, trickle 4.00s) and packet count (6 / 3 / 2). Horizontal wires scale `--dur` by 2.2/1.6 |
| `edges[].bps` | Bytes/sec when a number is known (log map 100 B/s → trickle, 100 MB/s → busy). Alias `bytes_per_sec` |
| `edges[].rate` | 0..1 occupancy when volume is a fraction, not a band |
| `edges[].bytes` | Expected payload size (log map 1 KiB → trickle, 1 GiB → busy) when rate is unknown |
| `keyframes[].t` | 0..1. Every frame with `t <= now` merges in order |
| `keyframes[].gates` | List of **active** gate ids (not full objects) |
| `keyframes[].nodes` | `{ id: { state, running_s, … } }` patches |
| `keyframes[].log` / `failures` / `footer` / `stages` / `timeline` | Replace that block |

## CLI

```text
render_flow.py html GRAPH.json -o out.html [--t 0.4 --paused]
render_flow.py bake GRAPH.json -o out.gif [--frames 16 --fps 8 --scale 0.5 --mp4]
render_flow.py self-test
```

`html` without `--paused` includes a 8s `--t` loop for a real browser.
`bake` always writes paused frames, a mid-loop PNG next to the GIF, and
optional MP4.

## Sanitization

Toolkit examples use generic labels (`proxy`, `app`, `db`, `worker`). Do
not put logins, employer names, or `/home/{login}` in shipped JSON.
