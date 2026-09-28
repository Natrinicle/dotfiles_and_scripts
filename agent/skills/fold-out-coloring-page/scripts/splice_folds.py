#!/usr/bin/env python3
"""Crop a fold-out coloring page on its fold lines and splice the outer panels.

No new ink. Folded preview is left+right (gate-fold-thirds) or the outer half
(horizontal-center).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


def _to_gray(im: Image.Image) -> np.ndarray:
    return np.asarray(im.convert("L"), dtype=np.float32)


def _ink_mask(gray: np.ndarray, thresh: float = 210) -> np.ndarray:
    return gray < thresh


def detect_vertical_folds(gray: np.ndarray) -> tuple[int, int] | None:
    """Find two dashed vertical lines near 1/3 and 2/3 width."""
    h, w = gray.shape
    ink = _ink_mask(gray)
    scores = []
    for x in range(w):
        col = ink[:, x]
        if col.mean() < 0.02 or col.mean() > 0.35:
            scores.append(0.0)
            continue
        transitions = np.abs(np.diff(col.astype(np.int8))).sum()
        scores.append(float(transitions) * (0.15 - abs(col.mean() - 0.08)))
    scores = np.array(scores)
    if scores.max() <= 0:
        return None

    third = w / 3.0
    window = max(8, int(w * 0.06))

    def best_near(target: float) -> int | None:
        lo = max(0, int(target - window))
        hi = min(w, int(target + window))
        if hi <= lo:
            return None
        x = lo + int(np.argmax(scores[lo:hi]))
        return x if scores[x] > scores.mean() + 0.5 * scores.std() else x

    left = best_near(third)
    right = best_near(2 * third)
    if left is None or right is None:
        return None
    if right - left < w * 0.2:
        return None
    return left, right


def detect_horizontal_fold(gray: np.ndarray) -> int | None:
    h, w = gray.shape
    ink = _ink_mask(gray)
    scores = []
    for y in range(h):
        row = ink[y, :]
        if row.mean() < 0.02 or row.mean() > 0.35:
            scores.append(0.0)
            continue
        transitions = np.abs(np.diff(row.astype(np.int8))).sum()
        scores.append(float(transitions) * (0.15 - abs(row.mean() - 0.08)))
    scores = np.array(scores)
    if scores.max() <= 0:
        return None
    target = h / 2.0
    window = max(8, int(h * 0.08))
    lo = max(0, int(target - window))
    hi = min(h, int(target + window))
    y = lo + int(np.argmax(scores[lo:hi]))
    return y


def splice_gate(im: Image.Image, folds: tuple[int, int] | None) -> Image.Image:
    w, h = im.size
    if folds is None:
        a, b = w // 3, (2 * w) // 3
    else:
        a, b = folds
    left = im.crop((0, 0, a, h))
    right = im.crop((b, 0, w, h))
    out = Image.new(im.mode, (left.width + right.width, h), "white")
    out.paste(left, (0, 0))
    out.paste(right, (left.width, 0))
    return out


def splice_horizontal(im: Image.Image, fold_y: int | None) -> Image.Image:
    w, h = im.size
    y = h // 2 if fold_y is None else fold_y
    return im.crop((0, 0, w, y))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    p.add_argument("--geometry", choices=["gate-fold-thirds", "horizontal-center"], default="gate-fold-thirds")
    p.add_argument("--out", required=True)
    p.add_argument("--folds", help="Manual pixel cuts, e.g. 400,800")
    p.add_argument("--detect-dashes", action="store_true", help="Try dashed-line detection instead of equal thirds")
    args = p.parse_args()

    src = Path(args.input)
    im = Image.open(src).convert("RGB")
    gray = _to_gray(im)

    if args.geometry == "gate-fold-thirds":
        folds = None
        if args.folds:
            a, b = (int(x) for x in args.folds.split(","))
            folds = (a, b)
        elif args.detect_dashes:
            folds = detect_vertical_folds(gray)
        out = splice_gate(im, folds)
        where = f"folds={folds or 'equal-thirds'}"
    else:
        fold_y = None
        if args.folds:
            fold_y = int(args.folds.split(",")[0])
        else:
            fold_y = detect_horizontal_fold(gray)
        out = splice_horizontal(im, fold_y)
        where = f"fold_y={fold_y or 'mid-height fallback'}"

    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest)
    print(f"wrote {dest} ({out.size[0]}x{out.size[1]}) {where}")


if __name__ == "__main__":
    main()
