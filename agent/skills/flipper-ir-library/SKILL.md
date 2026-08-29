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
it is never trusted to an image model.

If the `.ir` is raw / unparsed / AC-state (not NEC, NECext, Samsung32, RC5, RC6),
load **decoding-ir-protocols** before writing the unit README.

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
  encode_*.py         # only when the protocol is not a one-shot parsed command
```

New folders: `Air_V` not `Air V`. Leave existing spaced names; encode spaces as
`%20` in Markdown links.

`.ir` filename: `Brand_Model.ir` (underscores, model caps). No spaces.

## Workflow

1. Place the capture and photos in `Infrared/<Type>/<Brand>/<Model>/`.
2. If Flipper saved `type: raw` (or the remote is HVAC/AC/state-based), decode
   with **decoding-ir-protocols** first. Do not invent buttons.
3. Clean photos per `references/photos.md`. Transcribe the rating plate **before**
   any AI edit. Lookup FCC. Strip GPS. Rename `IMG*.jpg`.
4. Write the unit README (button map, protocol, IDs). If an encode script is
   required, say so and that Flipper cannot send it as parsed NEC.
5. Ensure a README exists at **every** ancestor (`Infrared/`, type, brand, model)
   per `references/readme-tree.md`. Add the unit to each index table.
6. After any add/rename/move, run `scripts/check_readme_links.py` from the pack
   root. Fix every broken link in the same change. Ancestor READMEs must not 404.

## Do not

- Redraw button icons or rating-plate glyphs with an image model.
- Composite tiny stickers (QC ovals, round seals) onto an AI-cleaned body —
  that produces ghosted/duplicated labels. Omit them; transcribe in the README.
- Commit camera originals with GPS EXIF.
- Leave a new folder without a README, or a parent README that still points at
  the old path.
- Synthesize IR codes unless **decoding-ir-protocols** proved the field. Mark
  synthesized buttons in the `.ir` comment and the unit README.

## Exemplars

When the workspace is this kind of pack, copy tone and tables from an existing
unit folder (simple parsed NEC vs raw HVAC with `encode_*.py`). Do not copy
personal names into new files.

## Additional resources

- `references/photos.md` — deskew, background, dirt, FCC, GPS, QC ghosting
- `references/readme-tree.md` — index README templates and 404 rules
- `scripts/check_readme_links.py` — relative Markdown link checker
- **decoding-ir-protocols** — raw capture bit maps and encode scripts
