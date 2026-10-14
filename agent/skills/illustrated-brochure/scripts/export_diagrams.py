#!/usr/bin/env python3
"""Export Dia SVG→PNG and Graphviz DOT→PNG at print resolution."""

from __future__ import annotations

import subprocess
from pathlib import Path


def export_dia(src: Path, width: int = 2200) -> Path:
    """cairo-png ignores --size. SVG then rsvg-convert gives print pixels."""
    svg = src.with_suffix(".svg")
    png = src.with_suffix(".png")
    subprocess.run(
        ["dia", "--filter=cairo-svg", f"--export={svg}", str(src)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["rsvg-convert", "-w", str(width), str(svg), "-o", str(png)],
        check=True,
    )
    return png


def export_dot(src: Path, dpi: int = 200) -> Path:
    png = src.with_suffix(".png")
    subprocess.run(
        ["dot", "-Tpng", f"-Gdpi={dpi}", str(src), "-o", str(png)],
        check=True,
    )
    return png
