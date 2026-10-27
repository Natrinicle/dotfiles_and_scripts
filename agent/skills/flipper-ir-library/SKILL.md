---
name: flipper-ir-library
description: >
  Use when adding Flipper Zero .ir captures, remote or device photos, or READMEs
  under an Infrared/ library; when cleaning camera photos of remotes or HVAC
  units; when looking up FCC IDs from a rating plate; when renaming Infrared
  folders; or when the user asks to document a new IR remote pack.
---

# Flipper IR library

Package Flipper captures into a browseable tree: one folder per unit, cleaned
photos, a README at every directory, and `.ir` files that actually load on the
Flipper. Discrete label text (FCC, model, serial) is transcribed and verified;
it is never trusted to an image model. Included user-manual pages are cleaned
and shipped when the capture folder has those shots.

If Flipper saved `type: raw`, run `scripts/correct_parsed_ir.py` before the
unit README. Leftover HVAC/state (not NEC, NECext, Samsung32, RC5, RC6, SIRC,
SIRC15, SIRC20) loads **decoding-ir-protocols**. Parsed SIRC is a button map,
same as NEC.

## Pack root

The pack root is the directory that contains `Infrared/` (or `infrared/`). Work
there. Layout:

```
Infrared/<Type>/<Brand>/<Model>/
  Brand_Model.ir
  README.md
  remote.jpg          # optional
  unit.jpg            # optional; add unit-front/rear/top/bottom/side as needed
  label.jpg           # pixel crop of the rating plate when IDs exist
  manual-1.jpg        # optional; cleaned included user-manual page/spread
  manual-2.jpg        # additional pages in reading order (manual-3.jpg, …)
  encode_*.py         # only when the protocol is not a one-shot parsed command
```

New folders: `Air_V` not `Air V`. Leave existing spaced names; encode spaces as
`%20` in Markdown links.

`.ir` filename: `Brand_Model.ir` (underscores, model caps). No spaces.

## Workflow

1. Place the capture and photos in `Infrared/<Type>/<Brand>/<Model>/`.
2. If Flipper saved `type: raw`, run `scripts/correct_parsed_ir.py UNIT.ir`
   (then `--write`). It promotes jittered NEC/NECext/Samsung32 to parsed and
   tags NEC-repeat-only keys. Leftover HVAC/state frames go to
   **decoding-ir-protocols**. Do not invent buttons or command bytes. See
   `references/parsed-ir-correct.md`.
3. Clean photos per `references/photos.md` (cutout procedure for dense I/O).
   Transcribe the rating plate **before** any AI edit. Lookup FCC. Strip GPS.
   Route a dump with local Ollama vision (`scripts/classify_shots.py`) so
   remote / unit / label / manual / skip is decided on-box. When originals
   include a user manual, instruction sheet, or leaflet, ship those pages as
   `manual-1.jpg`, `manual-2.jpg`, … (see **User-manual pages**). Keep camera
   originals in the unit folder as `Name.ignore.jpg` (gitignored via
   `*.ignore.*`). Do not delete them.
4. Write the unit README (button map, protocol, IDs). If an encode script is
   required, say so and that Flipper cannot send it as parsed NEC.
5. Ensure a README exists at **every** ancestor (`Infrared/`, type, brand, model)
   per `references/readme-tree.md`. Add the unit to each index table.
6. After any add/rename/move, run `scripts/check_readme_links.py` from the pack
   root. Fix every broken link in the same change. Ancestor READMEs must not 404.

## Do not

- Redraw button icons, rating-plate glyphs, or user-manual text with an
  image model. Paper cutouts use local rembg (BiRefNet), not Imagine.
- Call rembg's default `bria-rmbg` (non-commercial) or `withoutbg` (uploads
  the photo). Pin `birefnet-general`. Keep rembg on CPU so Ollama can use
  the GPU.
- Composite tiny stickers (QC ovals, round seals) onto an AI-cleaned body —
  that produces ghosted/duplicated labels. Omit them; transcribe in the README.
- Warp an oblique camera original onto a straight-on cleaned body. Screws,
  ear corners, and plate baselines will not line up (duplicate screws, dropped
  labels). Ask for a matching-angle shot instead.
- Paint over screws or chassis edges to hide a hand or background. That
  pixelates the hardware. Recut the mask; leave a sliver of hand if needed.
- Trace a dense I/O bottom (HDMI / DIGITAL OUT) per-column by luminance.
  That punches white holes in the legends. Use a smooth polyline under the lip.
- Erode (`MinFilter`) a chassis mask. It chews ear screws and corners.
- Put TV-only keys (TV input, TV power, volume on SIRC address `01`) in a
  player `.ir`. They are not the Blu-ray. Leave them unmapped.
- Commit camera originals with GPS EXIF. Keep them as `*.ignore.*` instead.
- Leave a new folder without a README, or a parent README that still points at
  the old path.
- Synthesize IR codes unless **decoding-ir-protocols** proved the field. Mark
  synthesized buttons in the `.ir` comment and the unit README.
- Invent NEC command bytes for repeat-only captures. Tag them
  `correct_parsed_ir:` and re-learn. Fill from `nec-button-maps.json` only
  when parsed siblings uniquely match a map.

## Exemplars

When the workspace is this kind of pack, copy tone and tables from an existing
unit folder (simple parsed NEC vs raw HVAC with `encode_*.py`). Do not copy
personal names into new files.

## Additional resources

- `references/photos.md` — deskew, background, dirt, FCC, GPS, QC ghosting,
  source-angle match, overlay hallucinations, user-manual pages
- `references/readme-tree.md` — index README templates and 404 rules
- `scripts/check_readme_links.py` — relative Markdown link checker
- `scripts/classify_shots.py` — local Ollama vision: remote/unit/label/manual/skip
- `scripts/cutout_manual.py` — rembg BiRefNet matte, deskew, white, no EXIF
- `scripts/correct_parsed_ir.py` — raw → parsed NEC/NECext/Samsung32 when
  timings uniquely match; `--self-test` then `--write` on the unit or `Infrared/`
- `references/parsed-ir-correct.md` — rewrite bar, repeat-only, map fill
- `references/nec-button-maps.json` — discrete maps; add only when uniquely proven
- **decoding-ir-protocols** — leftover HVAC/state bit maps and encode scripts
