#!/usr/bin/env python3
"""Cut a photographed paper leaflet onto white using a local rembg matte.

Usage:
  cutout_manual.py SRC DST [--long-edge 1600] [--quality 90]
                   [--model birefnet-general]

Keeps original paper pixels. Does not redraw printed text. Default model is
MIT BiRefNet-general (local ONNX). rembg's own default is BRIA RMBG-2.0
(non-commercial) — do not use that on a CC0 catalog. Do not use withoutbg
(remote API).

CPU onnxruntime only so a local vision LLM can keep the GPU.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from scipy import ndimage

# rembg 2.0 default session is bria-rmbg (RMBG-2.0, non-commercial).
# withoutbg uploads the photo. Neither belongs in this pack.
ALLOWED_MODELS = (
    "birefnet-general",
    "birefnet-general-lite",
    "isnet-general-use",
    "u2net",
    "silueta",
)
FALLBACK_MODELS = (
    "birefnet-general",
    "birefnet-general-lite",
    "isnet-general-use",
)
BLOCKED_MODELS = frozenset({"bria-rmbg", "withoutbg"})

REMBG_TOOL_PYTHON = Path.home() / ".local/share/uv/tools/rembg/bin/python"


def _ensure_rembg() -> None:
    """Re-exec under the uv-tool rembg interpreter when needed."""
    try:
        import rembg  # noqa: F401
    except ImportError:
        if REMBG_TOOL_PYTHON.is_file() and Path(sys.executable).resolve() != (
            REMBG_TOOL_PYTHON.resolve()
        ):
            os.execv(str(REMBG_TOOL_PYTHON), [str(REMBG_TOOL_PYTHON), *sys.argv])
        sys.exit(
            "rembg is not installed. Install a local ONNX build:\n"
            "  uv tool install --python 3.12 'rembg[cpu]'\n"
            "Then rerun. Do not use rembg's default bria-rmbg (NC) or withoutbg."
        )


def _largest_cc(mask: np.ndarray) -> np.ndarray:
    labeled, n = ndimage.label(mask)
    if n == 0:
        raise SystemExit("no paper pixels found")
    counts = np.bincount(labeled.ravel())
    counts[0] = 0
    keep = int(counts.argmax())
    return labeled == keep


def _corners(mask: np.ndarray) -> np.ndarray:
    ys, xs = np.nonzero(mask)
    pts = np.column_stack([xs.astype(np.float64), ys.astype(np.float64)])
    s = pts[:, 0] + pts[:, 1]
    d = pts[:, 0] - pts[:, 1]
    tl = pts[int(s.argmin())]
    br = pts[int(s.argmax())]
    tr = pts[int(d.argmax())]
    bl = pts[int(d.argmin())]
    return np.stack([tl, tr, br, bl])


def _homography(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    a = []
    for (x, y), (u, v) in zip(src, dst, strict=True):
        a.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        a.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, vt = np.linalg.svd(np.asarray(a, dtype=np.float64))
    h = vt[-1].reshape(3, 3)
    return h / h[2, 2]


def _warp_maps(
    corners: np.ndarray, long_edge: int
) -> tuple[np.ndarray, np.ndarray, int, int]:
    tl, tr, br, bl = corners
    width_top = float(np.linalg.norm(tr - tl))
    width_bot = float(np.linalg.norm(br - bl))
    height_l = float(np.linalg.norm(bl - tl))
    height_r = float(np.linalg.norm(br - tr))
    out_w = max(32, int(np.round(max(width_top, width_bot))))
    out_h = max(32, int(np.round(max(height_l, height_r))))
    # Warp near the shipped size; full-res map_coordinates is slow.
    m = max(out_w, out_h)
    cap = max(long_edge * 2, 1600)
    if m > cap:
        scale = cap / m
        out_w = max(32, int(np.round(out_w * scale)))
        out_h = max(32, int(np.round(out_h * scale)))
    dest = np.array(
        [[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]],
        dtype=np.float64,
    )
    hmat = _homography(corners, dest)
    hinv = np.linalg.inv(hmat)
    ys, xs = np.meshgrid(
        np.arange(out_h, dtype=np.float64),
        np.arange(out_w, dtype=np.float64),
        indexing="ij",
    )
    dest_h = np.stack([xs.ravel(), ys.ravel(), np.ones(xs.size)])
    src = hinv @ dest_h
    src = src[:2] / src[2]
    return src[1].reshape(out_h, out_w), src[0].reshape(out_h, out_w), out_h, out_w


def _warp(
    rgb: np.ndarray, mask: np.ndarray, corners: np.ndarray, long_edge: int
) -> np.ndarray:
    """Deskew original pixels and paint rembg-rejected samples white."""
    row_map, col_map, out_h, out_w = _warp_maps(corners, long_edge)
    maps = [row_map, col_map]
    channels = [
        ndimage.map_coordinates(
            rgb[:, :, c].astype(np.float32),
            maps,
            order=1,
            mode="constant",
            cval=255.0,
        ).reshape(out_h, out_w)
        for c in range(3)
    ]
    warped = np.clip(np.stack(channels, axis=2), 0, 255).astype(np.uint8)
    keep = ndimage.map_coordinates(
        mask.astype(np.float32),
        maps,
        order=1,
        mode="constant",
        cval=0.0,
    ).reshape(out_h, out_w)
    warped[keep < 0.5] = 255
    return warped


def _resize_long_edge(im: Image.Image, long_edge: int) -> Image.Image:
    width, height = im.size
    m = max(width, height)
    if m <= long_edge:
        return im
    scale = long_edge / m
    nw = max(1, int(np.round(width * scale)))
    nh = max(1, int(np.round(height * scale)))
    return im.resize((nw, nh), Image.Resampling.LANCZOS)


def _load_work_image(src: Path, infer_edge: int) -> Image.Image:
    im = Image.open(src)
    im = ImageOps.exif_transpose(im)
    im = im.convert("RGB")
    return _resize_long_edge(im, infer_edge)


def _matte(im: Image.Image, model: str) -> np.ndarray:
    """Return a boolean paper mask from a local rembg session."""
    from rembg import new_session, remove

    if model in BLOCKED_MODELS:
        raise SystemExit(
            f"{model} is blocked: bria-rmbg is non-commercial; "
            "withoutbg uploads the photo. Use birefnet-general."
        )
    session = new_session(model, providers=["CPUExecutionProvider"])
    mask_im = remove(im, session=session, only_mask=True, post_process_mask=True)
    if not isinstance(mask_im, Image.Image):
        mask_im = Image.fromarray(np.asarray(mask_im))
    alpha = np.asarray(mask_im.convert("L"))
    return alpha > 32


def paper_mask(
    im: Image.Image,
    model: str,
    min_frac: float,
) -> np.ndarray:
    """Largest rembg blob; try fallbacks if the matte is a tiny graphic."""
    models = (model,) if model != "auto" else FALLBACK_MODELS
    last_err = "no model produced a usable mask"
    for name in models:
        try:
            raw = _matte(im, name)
        except SystemExit:
            raise
        except Exception as exc:  # noqa: BLE001 — try the next local model
            last_err = f"{name}: {exc}"
            print(f"rembg {name} failed: {exc}", file=sys.stderr)
            continue
        frac = float(raw.mean())
        if frac < min_frac:
            last_err = f"{name}: mask fraction {frac:.3f} < {min_frac}"
            print(last_err, file=sys.stderr)
            continue
        seed = _largest_cc(raw)
        seed = ndimage.binary_closing(seed, iterations=4)
        seed = ndimage.binary_fill_holes(seed)
        # Trim a rembg halo (table lip). fill_holes already kept cover art.
        seed = ndimage.binary_erosion(seed, iterations=6)
        if float(seed.mean()) < min_frac:
            last_err = f"{name}: largest blob too small after cleanup"
            print(last_err, file=sys.stderr)
            continue
        print(f"using rembg model {name} (frac={seed.mean():.3f})", file=sys.stderr)
        return seed
    raise SystemExit(last_err)


def cutout(
    src: Path,
    dst: Path,
    long_edge: int,
    quality: int,
    model: str,
    min_frac: float,
    infer_edge: int,
) -> None:
    im = _load_work_image(src, infer_edge)
    rgb = np.array(im)
    mask = paper_mask(im, model, min_frac)
    if mask.sum() < 1000:
        raise SystemExit(f"mask collapsed: {src}")
    corners = _corners(mask)
    warped = _warp(rgb, mask, corners, long_edge)
    out = Image.fromarray(warped, mode="RGB")
    pad = 16
    canvas = Image.new(
        "RGB", (out.width + 2 * pad, out.height + 2 * pad), (255, 255, 255)
    )
    canvas.paste(out, (pad, pad))
    canvas = _resize_long_edge(canvas, long_edge)
    dst.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(
        dst,
        format="JPEG",
        quality=quality,
        optimize=True,
        progressive=False,
        subsampling=0,
    )


def main() -> int:
    _ensure_rembg()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("src", type=Path)
    p.add_argument("dst", type=Path)
    p.add_argument("--long-edge", type=int, default=1600)
    p.add_argument("--quality", type=int, default=90)
    p.add_argument(
        "--model",
        default="birefnet-general",
        help="rembg session name, or auto to try FALLBACK_MODELS in order",
    )
    p.add_argument(
        "--min-frac",
        type=float,
        default=0.12,
        help="reject a matte smaller than this fraction of the frame",
    )
    p.add_argument(
        "--infer-edge",
        type=int,
        default=3200,
        help="long-edge cap before rembg (model itself is 1024; 3200 ships ~1600)",
    )
    args = p.parse_args()
    if args.model not in ("auto", *ALLOWED_MODELS):
        raise SystemExit(
            f"blocked or unknown model {args.model!r}. "
            f"Allowed: auto {' '.join(ALLOWED_MODELS)}"
        )
    cutout(
        args.src,
        args.dst,
        args.long_edge,
        args.quality,
        args.model,
        args.min_frac,
        args.infer_edge,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
