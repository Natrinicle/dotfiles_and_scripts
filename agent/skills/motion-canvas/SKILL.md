---
name: motion-canvas
description: >
  Use when creating programmatic vector animations, explainer videos,
  code-driven motion graphics, or TypeScript generator scenes with Motion
  Canvas. Triggers: motion canvas, makeScene2D, yield* animation, explainer
  video, synchronized voice-over, @motion-canvas/2d, create-motion-canvas.
  Skip CSS/web UI motion (modern-web-guidance), labeled system-flow GIFs
  (system-flow-viz), print brochures (illustrated-brochure), unlabeled video
  (imagine reference_to_video), Obsidian canvases (json-canvas).
---

# Motion Canvas

TypeScript generators that draw vector scenes, then a Vite editor at
`http://localhost:9000/` for preview and export. Own-project copy only.

## Pick the picture

| Ask | Skill / tool |
|-----|----------------|
| Code-driven vector animation / explainer | **this skill** |
| CSS/HTML motion, view transitions, popover | **modern-web-guidance** |
| Labeled systems and data-flow GIFs | **system-flow-viz** |
| Print landscape PDF | **illustrated-brochure** |
| Unlabeled generated clip | **imagine** `reference_to_video` |
| Obsidian `.canvas` | **json-canvas** |

Do not grow those skills to cover Motion Canvas scenes.

## Local clone vs scaffold

A read-only mirror lives at `${HOME}/repos/external/motion-canvas` when this
host cloned it (MIT, snapshot recorded in `agent/THIRD-PARTY.md`). Do not
vendor that monorepo into this pack. Do not copy `packages/ffmpeg` (GPLv3)
into a toolkit.

**New animation project** (default):

```bash
npm init @motion-canvas@latest
cd <project-path>
npm install
npm start
```

TypeScript is the documented language. Editor: `http://localhost:9000/`.
Image-sequence export is the MIT built-in. Video via `@motion-canvas/ffmpeg`
is optional and GPLv3 — add it only when the user asked for a finished
mp4, and only in the **user project**.

**Hacking the library itself:** `npm install` then `npx lerna run build` in
the clone; `npm run template:dev` for the bundled editor.

## Scene shape

`src/project.ts` lists scenes. Each scene is a `makeScene2D` generator.
`yield` publishes a frame. `yield*` runs another generator (tweens, waits).

```tsx
import {Circle, makeScene2D} from '@motion-canvas/2d';
import {all, createRef, waitFor} from '@motion-canvas/core';

export default makeScene2D(function* (view) {
  const dot = createRef<Circle>();
  view.add(<Circle ref={dot} size={80} fill={'#e13238'} x={-200} />);
  yield* all(dot().position.x(200, 1), dot().fill('#e6a700', 1));
  yield* waitFor(0.25);
  yield* dot().position.x(-200, 1);
});
```

Node properties are signals: `node.fill()`, `node.fill('#fff', 1)` tweens
over one second. `all()` runs tweens together. `chain()` runs them in order.

Clone exemplars (when present):

- `packages/create/template-2d-ts/src/scenes/example.tsx`
- `packages/docs/docs/getting-started/quickstart.mdx`
- `packages/docs/docs/getting-started/flow.mdx`
- `packages/docs/docs/getting-started/signals.mdx`

## Verify

1. `npm start` and open the editor.
2. Play the scene. Check timing, layout, and text.
3. Export an image sequence (or ffmpeg video only if the user named it).
4. Read a frame. Fix overlap and unreadably small type. Re-export.

## Do not

- Call `image_gen` / `reference_to_video` for labeled, timed vector explainers
- Scaffold with `packages/ffmpeg` inside this pack
- Invent `{HOME}/repos/motion-canvas-toolkit`
- Treat CSS `@starting-style` / View Transitions as Motion Canvas (that is
  **modern-web-guidance**)
