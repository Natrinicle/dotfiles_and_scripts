#!/usr/bin/env python3
"""fpdf2 helpers for a landscape illustrated brochure."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from fpdf import FPDF
from PIL import Image

# Landscape Letter, points
W, H = 792.0, 612.0
M = 36.0

INK = (27, 31, 36)
CREAM = (247, 244, 238)
WHITE = (255, 250, 243)
AMBER = (197, 118, 26)
AMBER_DK = (122, 74, 16)
ROSE = (178, 58, 72)
ROSE_DK = (122, 36, 48)
TEAL = (31, 111, 100)
TEAL_DK = (19, 78, 72)
SLATE = (90, 98, 108)
LINE = (207, 198, 184)

_LATO_DIR = Path("/usr/share/fonts/truetype/lato")
_DEJAVU_DIR = Path("/usr/share/fonts/truetype/dejavu")


def font_files() -> dict[str, Path]:
    """Lato if installed, else DejaVu Sans."""
    lato = {
        "": _LATO_DIR / "Lato-Regular.ttf",
        "B": _LATO_DIR / "Lato-Bold.ttf",
        "I": _LATO_DIR / "Lato-Italic.ttf",
        "Black": _LATO_DIR / "Lato-Black.ttf",
    }
    if lato[""].is_file():
        return lato
    return {
        "": _DEJAVU_DIR / "DejaVuSans.ttf",
        "B": _DEJAVU_DIR / "DejaVuSans-Bold.ttf",
        "I": _DEJAVU_DIR / "DejaVuSans-Oblique.ttf",
        "Black": _DEJAVU_DIR / "DejaVuSans-Bold.ttf",
    }


def crop_whitespace(
    src: Path, dest: Path, bg: tuple[int, int, int] = CREAM, pad: int = 18
) -> Path:
    im = Image.open(src).convert("RGB")
    arr = np.asarray(im).astype("int16")
    delta = (
        (abs(arr[:, :, 0] - bg[0]) > 12)
        | (abs(arr[:, :, 1] - bg[1]) > 12)
        | (abs(arr[:, :, 2] - bg[2]) > 12)
    )
    ys, xs = np.where(delta)
    if ys.size == 0:
        dest.write_bytes(src.read_bytes())
        return dest
    min_x, max_x = int(xs.min()), int(xs.max())
    min_y, max_y = int(ys.min()), int(ys.max())
    w, h = im.size
    box = (
        max(0, min_x - pad),
        max(0, min_y - pad),
        min(w, max_x + pad + 1),
        min(h, max_y + pad + 1),
    )
    im.crop(box).save(dest, "PNG")
    return dest


class Brochure(FPDF):
    """Landscape cream page with kicker, cards, and fitted images."""

    def __init__(
        self,
        title: str = "Brochure",
        footer_left: str = "",
        page_count: int = 6,
    ) -> None:
        super().__init__(orientation="L", unit="pt", format="Letter")
        self.set_auto_page_break(auto=False)
        self.set_title(title)
        self._footer_left = footer_left or title
        self._page_count = page_count
        fonts = font_files()
        self.add_font("Lato", "", str(fonts[""]))
        self.add_font("Lato", "B", str(fonts["B"]))
        self.add_font("Lato", "I", str(fonts["I"]))
        self.add_font("LatoBlk", "", str(fonts["Black"]))

    def cream(self) -> None:
        self.set_fill_color(*CREAM)
        self.rect(0, 0, W, H, "F")

    def rounded_rect(self, x, y, w, h, r=8, style="F"):
        self.rect(x, y, w, h, style=style, round_corners=True, corner_radius=r)

    def footer(self) -> None:
        if self.page_no() == 1:
            return
        self.set_draw_color(*LINE)
        self.set_line_width(0.6)
        self.line(M, H - 28, W - M, H - 28)
        self.set_font("Lato", "", 9)
        self.set_text_color(*SLATE)
        self.set_xy(M, H - 24)
        self.cell(400, 12, self._footer_left)
        self.set_xy(W - M - 80, H - 24)
        self.cell(80, 12, f"{self.page_no()}   /   {self._page_count}", align="R")

    def kicker(self, text: str, color: tuple[int, int, int] = SLATE) -> None:
        self.set_font("Lato", "B", 10)
        self.set_text_color(*color)
        self.set_xy(M, 22)
        self.cell(400, 12, text.upper())

    def h1(self, text: str, y: float = 40) -> None:
        self.set_font("LatoBlk", "", 28)
        self.set_text_color(*INK)
        self.set_xy(M, y)
        self.cell(W - 2 * M, 32, text)

    def body(
        self,
        x: float,
        y: float,
        w: float,
        text: str,
        size: float = 12.5,
        leading: float = 17,
    ) -> float:
        self.set_font("Lato", "", size)
        self.set_text_color(*INK)
        self.set_xy(x, y)
        self.multi_cell(w, leading, text, align="L")
        return self.get_y()

    def italic(
        self,
        x: float,
        y: float,
        w: float,
        text: str,
        size: float = 12,
        leading: float = 16,
    ) -> float:
        self.set_font("Lato", "I", size)
        self.set_text_color(*SLATE)
        self.set_xy(x, y)
        self.multi_cell(w, leading, text, align="L")
        return self.get_y()

    def card(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        fill: tuple[int, int, int],
        label: str,
        label_color: tuple[int, int, int],
        body: str,
    ) -> None:
        self.set_fill_color(*fill)
        self.set_draw_color(*fill)
        self.rounded_rect(x, y, w, h, 8, style="F")
        self.set_font("Lato", "B", 10)
        self.set_text_color(*label_color)
        self.set_xy(x + 14, y + 12)
        self.cell(w - 28, 14, label.upper())
        self.set_font("Lato", "", 11.5)
        self.set_text_color(*INK)
        self.set_xy(x + 14, y + 30)
        self.multi_cell(w - 28, 15.5, body, align="L")

    def fit_image(
        self,
        path: Path,
        x: float,
        y: float,
        max_w: float,
        max_h: float,
        valign: str = "center",
    ) -> float:
        im = Image.open(path)
        iw, ih = im.size
        scale = min(max_w / iw, max_h / ih)
        w, h = iw * scale, ih * scale
        ix = x + (max_w - w) / 2
        if valign == "top":
            iy = y
        elif valign == "bottom":
            iy = y + max_h - h
        else:
            iy = y + (max_h - h) / 2
        self.image(str(path), x=ix, y=iy, w=w, h=h)
        return iy + h

    def rule(
        self, x: float, y: float, w: float, color: tuple[int, int, int] = LINE
    ) -> None:
        self.set_draw_color(*color)
        self.set_line_width(1.2)
        self.line(x, y, x + w, y)
