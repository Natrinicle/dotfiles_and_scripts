# Findings from the first working pages

## What actually registered

The page that worked for the frog was not a single stretched body. It was two facing frogs with the surprise (tongues + fly) in the gap, dashed folds through each face, outer panels still reading as the closed subject when folded.

When a one-line fix is needed, edit that working unfold and change only the named detail. Rebuilding from the closed page often redraws the outer halves and loses registration.

## Model failure modes

- Asking for folded view as a second generate produces a different character.
- Asking to split and fill often drops the mid-body and leaves two bookend halves.
- Asking to fix the tongue on an unfold restyles spots, feet, and faces unless the prompt forbids every other change.
- Fold dashes follow the face curve unless the prompt says ruler-straight, 90 degrees to the page.

## Working edit prompt pattern

Keep X identical. Change ONLY Y. Do not restyle faces, folds, feet, spots, or outer segments.

## Geometry that survived fold

Straight vertical dashes through each figure. Landscape page. Surprise lives between the figures (or in the opened mid-strip) so folding the outer thirds hides it.

## Splice script

Prefer equal-width thirds or explicit `--folds x,y`. Dashed-line detection picks up legs and eye lines. Default is equal thirds.
