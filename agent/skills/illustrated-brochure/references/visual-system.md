# Visual system

Letter landscape, 792×612 pt. Margins 36 pt.

## Color

| Token | Hex | Default use |
|-------|-----|-------------|
| Ink | `#1B1F24` | Type |
| Cream | `#F7F4EE` | Page |
| Slate | `#5C6570` | Secondary type |
| White | `#FFFBFA` | Cards |
| Accent 1 (amber) | `#C5761A` | First path, first option, first phase |
| Accent 2 (rose) | `#B23A48` | Second path, failure, warning |
| Accent 3 (teal) | `#1F6F64` | Third path, the working sequence, success |
| Gold | `#D4A017` | Start nodes |

**field-story** maps accent 1/2/3 → original / first rewrite / path to finish.
**process** maps them → phase 1 / 2 / 3 (cycle if more steps).
**comparison** maps them → option A / B / C.
**incident** maps them → expected / failure / repair.

Tint fills: amber `#F3DFC1`, rose `#F3D0D4`, teal `#D7EBE7`, gold `#F6E7B8`.
Ink on those fills: `#6B3E0A`, `#6B1F2A`, `#0F3D38`.

Do not add extra hues. Color is structure.

## Type

Lato, then DejaVu. Sizes: kicker 11, display 36, card title 16, body 12.5
leading 17, footer 9. Body align left. Measure overflow with `get_y()`.

## Layout

Cover: dark rail ~240 pt plus cream column. The rail kicker is the topic or
document type, never a product, employer, or repo name. Interior: cream,
colored rule under the title, two cards plus a figure, or a full-width figure.

Fit images with a letterbox helper. Do not stretch. Do not let intro text
overlap the figure. Do not put a color key over body copy.

fpdf2 2.8.x has no public `rounded_rect`. Wrap `rect(..., round_corners=True,
corner_radius=r)`.
