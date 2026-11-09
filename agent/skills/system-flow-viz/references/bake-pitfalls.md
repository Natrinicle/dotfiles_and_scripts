# Bake pitfalls

Headless Chromium screenshot of `file://` HTML does **not** run inline JS.
`--dump-dom` stays at the HTML defaults. Live `applyState(t)` never runs.
Bake frozen documents instead.

## Frozen frame

`render_flow.py` re-renders the graph at `t = i / frames` with `paused=True`:

- `:root { --t: 0.nnnn; --play: paused; }`
- no `<script>`
- keyframes with `keyframe.t <= t` already merged into node states, footer,
  log, gates, failures

CSS packets still move in a real browser. For a still, pause them:

```css
.pkt { animation-play-state: var(--play); }
.pkt.drop {
  animation: fall var(--dur) linear infinite;
  animation-delay: calc(var(--d) - var(--dur) * var(--t));
}
```

`--play: paused` plus a negative delay equal to `--t` of the cycle freezes
each dot on the wire.

## Class names

| Wrong | Right |
|-------|-------|
| `class="gate<!--G1--> active<!--/G1-->"` | `class="gate active"` on the live gate |
| Meter/p-label class `split` when `.split { width: 640px }` is the fan-out wire | A distinct class (`hot`) for meter fills |
| HTML comments inside attribute values | Re-render the attribute |

`test_render_flow.py` asserts `class="gate active"` and rejects comments
inside `class`.

## Chromium

```text
chromium --headless=new --no-sandbox --disable-gpu \
  --window-size={width},{height} \
  --screenshot={frame}.png file://{absolute-html}
```

`--window-size` must match `graph.width` / `graph.height`. A 1200×1500
document in a 800×600 window crops the footer.

## ffmpeg (version 9)

`palettegen` with `stats_mode=single` can exit 234. A single PNG filename
needs an image2 sequence flag:

```text
ffmpeg -y -framerate 8 -i frames/f%02d.png -vf palettegen \
  -update 1 -frames:v 1 palette.png
ffmpeg -y -framerate 8 -i frames/f%02d.png -i palette.png \
  -lavfi paletteuse=dither=bayer -gifflags -offsetting out.gif
```

`--scale 0.5` (the bake default) halves pixels for a chat-sized GIF.
Pass `--scale 1` for a 1:1 capture.

## Verify

1. Mid-loop PNG still: every label readable, packets visible on wires,
   active gate filled, footer counts match the keyframe.
2. GIF loops. Sixteen frames at 8 fps is a 2s loop.
3. Do not treat baked numbers as live telemetry unless the graph said so.
