---
name: code-drawn-media
description: >
  Use when the user asks for a browser game, short film, or 3D walkthrough
  built entirely in code (one HTML file, three.js, pure JS/Python frames,
  floor-plan tour) with no stock assets. Triggers: from-scratch game,
  code-drawn video, Playwright ffmpeg frames, skeletal walk cycle, attach
  photos or a PDF and make a film. Skip Motion Canvas scenes (motion-canvas),
  unlabeled generated clips (imagine), labeled system GIFs (system-flow-viz).
---

# Code-drawn media

Build the thing in code so every frame, mesh, texture, and sound is generated.
The format (game, video, walkthrough) is the last step. Attach real material.
Keep the first ask short.

## Pick the picture

| Ask | Skill / tool |
|-----|----------------|
| One-file three.js game, from-scratch models/sound | **this skill** |
| Short film whose frames are a function of time | **this skill** (Playwright + ffmpeg) |
| Browser 3D tour from a floor plan + photos | **this skill** |
| TypeScript vector explainer / `makeScene2D` | **motion-canvas** |
| Labeled systems and data-flow GIFs | **system-flow-viz** |
| Unlabeled generated clip or still | **imagine** |
| Print landscape PDF | **illustrated-brochure** |
| Whole app as PM tickets | **vibe-pm** (host) |

Do not grow those skills to cover from-scratch HTML/JS/Python media.

## Before the first file

1. Collect attachments (photos, PDF, floor plan, style stills, a repo). Short
   prompt plus real material beats a long prompt with no references.
2. Write a **task brief** for a capable implementer who has not seen the
   project. Do not "optimize the prompt" into a tutorial.
3. Name win **and** lose (game), shot length (video), or measurements to
   confirm (walkthrough). Stop and ask when those are missing.
4. Cap time or money before a long run. Start at effort **high**. Raise to
   max only where a measured difference exists. Plan on the strongest coding
   model available; long file-write or frame-render loops may use a cheaper
   sibling. Routing: **model-router**.
5. Load `references/prompts.md` and fill the matching starter.

## Build rules

- One deliverable the user can open: a single HTML file, or an MP4 plus the
  HTML/JS that produced it.
- Models, textures, sound, and music live in code. No CDNs, no stock packs,
  no copied pixels from the attachments (style and facts only).
- Characters: skeletal animation. Inspect single frames of walk/attack
  cycles until the motion is right, then trust the loop.
- Video: each frame is `f(t)`. Render stills first. Playwright captures;
  ffmpeg stitches. HTML-only preview is allowed when the user has no
  Playwright; say that it is not frame-perfect.
- Walkthrough: list every measurement read from the plan and wait for
  confirm before modeling. Then eye-height shots vs the photos.
- Impact sounds may lag the picture by one frame as a **choice**. Do not
  bake that delay into every hit.

## Done when

Load `references/checks.md`. A playable start-to-finish run, a contact sheet
of every shot, or three confirmed rooms. Report the next upgrade. Do not
build it yet.
