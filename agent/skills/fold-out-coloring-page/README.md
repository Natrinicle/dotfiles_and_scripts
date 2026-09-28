# Fold-out coloring pages

Agent skill plus a small splice script for surprise fold-out coloring sheets (Temu-style pull/unfold pages).

## Install

Copy this directory to `{AGENT_HOME}/skills/fold-out-coloring-page/` or run the parent toolkit `install.sh --agent`.

## Use

Ask the agent for a fold-out coloring page and name the closed subject plus the reveal. It generates the closed page first, then splits that drawing and fills only the gap.

To preview the folded state from a saved unfold raster:

```bash
python3 scripts/splice_folds.py unfolded.png --geometry gate-fold-thirds --out folded.png
```

Needs Python 3, Pillow, and numpy.

## Print

US letter, color first, fold the outer thirds inward so the original halves meet.
