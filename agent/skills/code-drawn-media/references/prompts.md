# Starter briefs

Fill the bracketed slots. Keep the rest. These are starting briefs, not
vendor-locked prompts. Swap the idea line; keep the checks.

## Game (one HTML file, three.js)

```
Make a small 3D game that runs in the browser as one HTML file, using three.js.

The idea: [ONE SENTENCE: who the player is, what they do, how they win and how they lose].

Build everything in code: models, textures, sound effects and music. No outside assets.

Characters use skeletal animation. Before moving on, render single frames of the walk and attack cycles and check them one by one until the motion looks right.

When it is playable, play it: take screenshots at the start, the middle and the end, fix whatever looks wrong, then play again.

Stop when someone can play it start to finish. Tell me what to improve next, but do not do it yet.
```

Idea line must include how the player **loses**. Example: "Lighthouse keeper on one stormy night. Climb, refill the lamp, fix shutters. Win if the lamp still burns at dawn; lose if it is dark for ten seconds."

## Video (code frames → MP4)

Need Node, Playwright Chromium, and ffmpeg on PATH. Claude app / a browser
preview can still run the HTML; screen-record that only as a first look.

```
Make a [30] second video about [STORY, PLACE, OR PRODUCT].

Attached: [style images / PDF with notes and photos]. Use them for look and facts. Do not copy any image directly.

Rules: every frame is drawn in code (JavaScript or Python), no stock footage, no outside assets except the attachments. Sound is made in code too.

First write a shot list: what we see, for how long, and what sound plays. Show it and wait.

After go: render one frame from each shot, look at them, fix what is off. Only then render the full video at 1080p, 60 fps, with sound.
```

Longer timing brief (after the short version works):

```
Make a 30 second video, 1920x1080, 60 fps, with sound.

STORY: [ONE SENTENCE: what happens, and what the viewer should feel at the end].

LOOK: [3 colors in hex, one font, one sentence about light and texture]. Use the attached images for style only.

SHOTS (seconds):
0-3    hook: [the single most striking image]
3-10   [what we learn]
10-20  [the turn or the surprise]
20-27  [the payoff]
27-30  a held final frame

MOTION: ease in and out, no constant-speed moves, one main movement per shot.

SOUND: made in code, no samples. Music at about [100] BPM, cuts on the beat.
Optional: each impact sound one frame after the picture that causes it.

BUILD: one HTML file where every frame is a function of time. Render with Playwright, stitch with ffmpeg.

CHECK: before the full render, show one frame from each shot. After, look at a contact sheet and fix anything off.
```

Deps (any OS that has them):

```bash
node -v && ffmpeg -version
npm init -y
npm i -D playwright
npx playwright install chromium
```

## 3D walkthrough (floor plan)

```
Here is a floor plan [ATTACH] and photos of the space [ATTACH].

Build it as a 3D model to scale that I can walk through in the browser: walls, doors and windows exactly where the plan puts them, materials matched to the photos, soft daylight through the windows.

First, list every measurement read from the plan and anything unsure. Wait for confirm before building.

When built, send screenshots from three rooms at eye height. Compare them with the photos and fix anything that does not match before calling it done.
```

Blurry plans: guess nothing. List the uncertain lengths and wait.

## Source

Methods adapted from a public 2026-11 roundup of one-shot code-drawn games,
films, and walkthroughs (high-capability coding models, short ask plus
attachments, frame checks). Starter text is rewritten for this pack.
