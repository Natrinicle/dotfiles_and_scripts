# Photos

Product shots of remotes and units. Allowed edits: straighten/deskew, white (or
transparent) background, wipe dirt/grime/dust, crop, JPEG optimize. **Do not**
change button artwork, printed icons, or rating-plate text.

Load the Imagine skill when calling `image_edit` / `image_gen`.

## Order of operations

1. **Read the originals.** Crop the rating plate at full resolution. Transcribe
   every ID into notes *before* any generative edit.
2. **FCC / regulatory lookup.** Search `fccid.io` / `fcc.report` for brand +
   model. The oval under an FC logo is often a factory number, not the FCC ID.
   A grant looks like `2A342-H1`. Record both: what is printed, and the grant.
3. **Generative cleanup** (optional): one `image_edit` per photo. Prompt only
   the allowed edits. Name the printed labels that must stay identical.
4. **Verify** the result against the original: button icons, **screws**, ear
   corners, model string, FCC oval, serial, BIS/CE marks, port-legend baselines.
   Count screws. If any glyph is wrong, do **not** re-prompt the image model to
   “fix the text.”
5. **Composite discrete text** by pasting a pixel crop of the original plate
   (or `label.jpg`) onto the cleaned housing. That is the only safe way to keep
   IDs exact. A dense rear I/O / rating face (serial, Contains FCC ID, port
   legends) will garble under `image_edit`. Do not ship that beauty shot.
   Keep original pixels for the panel and put IDs in `label.jpg`. Overlay only
   the inner panel: never cover ear screws or the center chassis screw.
6. **Strip GPS.** Phone JPEGs often have EXIF GPS. Save new JPEGs (quality ~90,
   long edge 800–1600) with no EXIF. Confirm `Image.info` has no `exif`/`gps`.
7. **Rename.** Shipped files: `remote.jpg`, `unit.jpg`, `unit-front.jpg`,
   `unit-rear.jpg`, `unit-top.jpg`, `unit-bottom.jpg`, `unit-side.jpg`,
   `label.jpg`. Camera originals stay in the **same unit folder** as
   `IMG….ignore.jpg` (or `Name.ignore.jpeg`). Pack `.gitignore` has `*.ignore.*`.
   Do not delete the originals. Do not commit them.

`label.jpg` is a tight crop of the real sticker (contrast/sharpen OK). It is
the source of truth for IDs even if the beauty shot omits a mark.

## QC labels and small stickers

Compositing a small oval/circle sticker onto an AI-cleaned body **ghosts**: the
model’s garbled sticker remains and the overlay doubles it (seen with Q.C.
PASSED ovals).

**Preferred:** omit QC / round inspection stickers from the beauty shot. Fill
with matching plastic. Transcribe the stamps in the unit README
(“on the hardware; omitted from `unit-bottom.jpg`”).

**Avoid:** stacking an original oval on top of an already-hallucinated oval.

Larger rectangular rating plates *can* be composited when the crop is tight
and the dest rect matches the plate, not surrounding housing.

## Source angle and coverage

The shipped view must come from a source shot at **that same angle**. Do not
warp a downward/oblique capture onto a straight-on cleaned body (Sony
UBP-X700): screws stack, ear corners overlap, and the rating plate sits too
low.

If the source is insufficient, **stop and tell the user** what to shoot. Do
not guess. Say so when:

- The camera looks down on a panel you need straight-on (or the reverse).
- A hand, cable, or shadow covers a screw, ear, or legend.
- A needed face is missing (rear I/O, rating plate, remote).
- Lighting is so uneven that a cutout cannot keep chassis edges.

Ask for a matching-angle shot, camera level with the face, full unit in
frame. Keep using the originals you have for `label.jpg` and transcription.

Prefer a cutout of the matching-angle original onto white over compositing
that original onto a different-angle beauty body.

If two matching-angle shots exist and a hand covers opposite ears, **pick the
frame whose critical side is uncovered** (X700: `…132659` hand-on-left vs
`…135237` hand-on-right). Do not stitch two frames unless keypoints match; a
clean single-source cutout beats a composite.

## Cutout procedure (dense I/O / rear panel)

Use this instead of `image_edit` on a face that has serial, FCC, HDMI legends,
or screws.

1. **Pick the source** at the shipped angle. Deskew from the top-left and
   top-right chassis corners (small `atan2` rotate).
2. **Mask the chassis only.** Follow black plastic. Exclude hands, tiles,
   sheets, and cables.
3. **Side / ear edges:** trace the leftmost (or rightmost) dark chassis pixel
   down the ear. That keeps the octagonal ear and the screw. Do **not**
   `MinFilter` / erode the mask (it chews screws). Gaussian blur ≤ 0.5 px is
   enough for anti-aliasing.
4. **Bottom of a legend strip (HDMI, DIGITAL OUT, CAN ICES):** do **not**
   trace luminance per column. That path jags and punches white holes in the
   silver plate. Use a **few smooth polyline points** clearly *below* every
   glyph and *above* the tile/thumb. HDMI silver is mid-grey (~120); tile is
   bright (~160+). Include the black lip under the silver plate.
5. **Paste onto white.** Light contrast (≤ 1.05) is fine. Do not extra-sharpen
   screws. Do not fill “skin” pixels on the ear — that pixelates the screw.
   Leave a sliver of hand rather than painting the hardware.
6. **Ship** long-edge 1600 JPEG, no EXIF/GPS. Keep the camera file as
   `Name.ignore.jpg` in the unit folder.

`label.jpg` stays a tight crop of original plate pixels (contrast/sharpen OK).

## Overlay hallucinations

After any composite or `image_edit`, hunt for **duplicates and seams** against
the source:

- Two screws where the hardware has one (ear screws, center chassis screw).
- A second HDMI / VIDEO / DIGITAL OUT legend row under the real plate.
- A rectangular overlay that does not follow the chassis; black tabs hanging
  into the background.
- Serial, FCC ID, or model string that does not match `label.jpg`.
- Overlay covering an ear so the original screw and the beauty-body screw
  both show.

If you see any of those, recut or drop the overlay. Do not paint screws or
edges to hide a hand — that pixelates the hardware (left ear of the X700).
Leave a sliver of hand rather than a chewed screw.

## Dirt vs identity

Wipe scuffs, dust, fingerprints, and handwritten marker on blank plastic
(“Failing LCD”, unit names in paint). Do not invent a brand wordmark on a
blank shell. Do not “clean” text by regenerating it.

## Check

| Must remain | How |
|-------------|-----|
| Button icons / d-pad glyphs | Visual diff vs original |
| Screws / ear corners | Same count and seats as the source; no doubles |
| Model, serial, FC oval, BIS | Match the pre-edit transcription and `label.jpg` |
| Port layout and legend rows | Same count and order; one HDMI/DIGITAL OUT row; no white bites in the silver plate |
| No GPS | PIL/identify: no gps/exif on shipped JPEGs |
