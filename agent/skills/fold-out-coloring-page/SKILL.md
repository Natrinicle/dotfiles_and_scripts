---
name: fold-out-coloring-page
description: Generate surprise fold-out coloring pages where the folded picture and the unfolded reveal share outlines and register on the fold. Use when the user asks for fold-out, foldable, unfolding, pull-tab, accordion, or hidden-surprise coloring pages like Temu magic fold-out books, dragon-with-flames or apple-with-worms reveals, or a cute/shocking/revealing inside when opened.
---

# Fold-out coloring pages

One-sided printable line art for kids. Closed picture first. Unfold by splitting that same drawing and filling only the new gap. Folded view is never a second guessed drawing.

## Lock first

1. Subject — complete closed picture
2. Reveal — what appears only after the split
3. Geometry — default gate-fold-thirds
4. Cut axis — usually the vertical midline

Examples that work:

- Robot, sealed. Reveal is circuits in the opened chest gap.
- Frog, sitting, mouth closed. Reveal is one unforked tongue grabbing a fly.
- Apple. Reveal is worms in the core strip.
- Dragon. Reveal is flame in the opened-mouth strip.

## Pipeline

Do not reorder.

1. Generate the CLOSED coloring page. No surprise. No fold lines required. Save the image id. This is the folded view.
2. Edit that same id. Split down the cut axis. Slide the halves to the outer thirds. Do not redraw those halves.
3. Fill the gap with the missing mid-body of the same figure, then the reveal on that body. Reveal lines must meet the cut-edge features (mouth corners, chest plates).
4. Draw fold marks as ruler-straight dashed lines, 90 degrees to the page edge. Vertical on landscape, horizontal on portrait. Never curve with anatomy.
5. Optional check: `python3 scripts/splice_folds.py UNFOLDED.png --out FOLDED.png` should look like step 1.

Coloring-page rules on every generate and edit: white background, bold even black outlines, no gray, no color, large colorable shapes, no text in the drawing.

Print: landscape letter unless the lock says portrait. Color first. Fold the outer thirds inward so the original halves meet and hide the reveal.

## Revisions

- User says an unfolded page is already right except one named detail (tongue shape, fold dashes): edit THAT page and change only that detail.
- Otherwise go back to the closed image id and run the split-and-fill again.
- Never edit a broken unfold to invent new outer halves.

## Anatomy

Real animals keep real anatomy. A frog tongue is one sticky ribbon attached at the front of the mouth, slightly paddle-shaped at the tip. Not forked. Not two spiral tongues that meet like a snake tongue.

## Tone

Cute, shocking, or revealing. Kid-safe unless the user clearly asked for adult tone. No sexual content involving minors.

## Anti-patterns

- Generating the surprise page first
- A second model call that shows the folded version
- Redrawing outer halves during a fill or a one-line fix
- Empty center with a floating tongue or gadget
- Two unrelated characters facing each other when the lock was one character (unless the user kept that layout on purpose)
- Curved fold dashes that follow a face
- Color or gray shading

## Scripts

`scripts/splice_folds.py` — crop on fold X (default equal thirds) and join the outer panels. No new ink.

```bash
python3 scripts/splice_folds.py unfolded.png --geometry gate-fold-thirds --out folded.png
```
