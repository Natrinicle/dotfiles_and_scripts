# Diagrams

## Which tool

| Need | Tool |
|------|------|
| Narrative flow (“then this happened”) | Dia 0.98 flowchart |
| Side-by-side options or a scorecard | Graphviz `dot` |

Do not put a title in the Dia canvas if the PDF already has an h1. Duplicate
titles steal height.

Field-story default: one Dia per path page, Graphviz for the cover overview
and the last-page table. Process default: one Dia per step page, Graphviz for
the cover overview. Comparison default: Graphviz for the overview and
scorecard, Dia only if an option has a real fork.

## Dia

Use `scripts/dia_flowchart.py`. Boxes, ellipses, diamonds (`obj_bb` 3, 2, 4).
Diamond arrows: **west and east** only. North/south on a diamond lands on the
vertex and looks like a stray line.

Export:

```bash
dia --filter=cairo-svg --export=foo.svg foo.dia
rsvg-convert -w 2200 foo.svg > foo.png
```

`cairo-png` ignores `--size`. Always SVG then raster. Crop cream margins so
the PDF helper can letterbox.

## Graphviz

`dot -Tpng -Gdpi=200`. Clusters for side-by-side. For stacked rows,
`newrank=true` plus invisible hub edges so siblings share a rank. HTML labels
for scorecards.

Keep node labels to one idea. If a label needs a comma, it is two nodes.

## Color

Fill from `visual-system.md`. Black edges, 2.2 pt. No extra hues.
