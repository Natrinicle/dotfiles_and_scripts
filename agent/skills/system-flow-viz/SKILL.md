---
name: system-flow-viz
description: >
  Use when the user asks to visualize data flow paths, traffic between systems,
  flows between systems, a packet-on-wire dashboard, a CSS tree
  GIF of services coming to life, unit activation, compose-stack traffic,
  agent routing, or a bootvine-like pending tree plus timeline. Skip print
  brochures (illustrated-brochure), Obsidian canvases (json-canvas), and
  unlabeled photos (imagine image_gen).
---

# System flow visualization

Labeled HTML/CSS dashboards of **systems and the data-flow paths between
them**. Exact names, states, counts, and arrows stay in code. Image models
do not draw this. Shipped preview: `docs/compose-stack.gif` (HTML next to it).

## Pick the picture

| Ask | Skill / tool |
|-----|----------------|
| Data flow paths, traffic between systems | **this skill** (default `combo`) |
| System names, states, counts, arrows, packets | **this skill** (HTML/CSS) |
| Units lighting up, packets on wires, looping GIF | **this skill** (`render_flow.py bake`) |
| Print landscape PDF of a process | **illustrated-brochure** |
| Obsidian `.canvas` | **json-canvas** |
| Unlabeled photo / illustration | **imagine** `image_gen` |
| Unlabeled motion of a scene | **imagine** `reference_to_video` |

**REQUIRED:** **imagine** for the code-vs-generation rule. This skill owns
the dashboard grammar. Brochure page recipes stay on **illustrated-brochure**.
Canvas JSON stays on **json-canvas**.

## Modes

| Mode | When | Grammar |
|------|------|---------|
| `tree` | Many units activating, booting, shutting down | Nested wait-on tree, stages, slowest-unit timeline, failure panel, footer census |
| `packet` | A handful of systems talking | Cards, wires, CSS packets, optional gate rail, session log |
| `combo` | Both (default for "data flow paths" / "flows between systems") | Tree plus packet strip plus timeline |

Tree grammar follows bootvine (live pending tree instead of a log wall):
nest each unit under the unit waiting on it, milestone rows open levels,
keep a timeline of the slowest runs in the leftover space, put last error
lines in a failure panel. Packet grammar follows the advisor-style
dashboard: color roles, packets on wires, gates on a rail. Packet speed
follows expected volume on each edge.

Details: `references/visual-system.md`. Graph JSON: `references/graph-schema.md`.

## Workflow

1. Infer systems and `talks` edges from the conversation, compose file, or
   code. Name states (`waiting` / `running` / `done` / `failed` / `blocked`).
2. Pick `tree`, `packet`, or `combo`. Default `combo` for "data flow paths",
   "visualize the data flow", or "traffic between systems."
3. Set each edge's expected volume (`high` / `medium` / `low`, a 0..1
   `rate`, or `bps`). Busier pipes drop faster and denser; trickle pipes
   drop slower with fewer dots. When the user gives no numbers: user-facing
   HTTP(S) is `high`, store/query is `medium`, queues and cron are `low`.
4. Write `examples/`-shaped JSON (copy `examples/compose-stack.json`).
5. Render HTML, then bake a GIF when motion is the point.

```bash
python3 "${AGENT_HOME}/skills/system-flow-viz/scripts/render_flow.py" html \
  graph.json -o /tmp/flow.html
python3 "${AGENT_HOME}/skills/system-flow-viz/scripts/render_flow.py" bake \
  graph.json -o /tmp/flow.gif --mp4
python3 "${AGENT_HOME}/skills/system-flow-viz/scripts/render_flow.py" self-test
```

6. Open the PNG still and read every label. Fix overlap, clipping, and
   wrong state glyphs. Re-bake. Do not ship a first frame unread.

## Bake rules

Chromium `file://` screenshots do **not** run inline JS. Frozen frames are
static HTML: `--play: paused` and `--t` on `:root`. CSS packets use
`animation-delay: calc(var(--d) - var(--dur) * var(--t))`. Gate highlight is
`class="gate active"`, never a comment inside `class`. ffmpeg palettegen
needs `-update 1 -frames:v 1`. Full list: `references/bake-pitfalls.md`.

## Do not

- Call `image_gen` or `reference_to_video` for labeled system diagrams
- Dump a scrolling log as the primary picture
- Put personal names, employer names, or absolute homes in the graph JSON
  that ships with a toolkit
- Copy bootvine source (GPL-3.0-or-later). Reuse the visual grammar only
- Grow **illustrated-brochure** or **json-canvas** to cover this dashboard
