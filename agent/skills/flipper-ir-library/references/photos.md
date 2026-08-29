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
4. **Verify** the result against the original: button icons, model string, FCC
   oval, serial, BIS/CE marks. If any glyph is wrong, do **not** re-prompt the
   image model to “fix the text.”
5. **Composite discrete text** by pasting a pixel crop of the original plate
   (or `label.jpg`) onto the cleaned housing. That is the only safe way to keep
   IDs exact.
6. **Strip GPS.** Phone JPEGs often have EXIF GPS. Save new JPEGs (quality ~90,
   long edge 800–1600) with no EXIF. Confirm `Image.info` has no `exif`/`gps`.
7. **Rename.** `remote.jpg`, `unit.jpg`, `unit-front.jpg`, `unit-rear.jpg`,
   `unit-top.jpg`, `unit-bottom.jpg`, `unit-side.jpg`, `label.jpg`. Delete
   `IMG*.jpg` only after the replacements exist and verify.

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

## Dirt vs identity

Wipe scuffs, dust, fingerprints, and handwritten marker on blank plastic
(“Failing LCD”, unit names in paint). Do not invent a brand wordmark on a
blank shell. Do not “clean” text by regenerating it.

## Check

| Must remain | How |
|-------------|-----|
| Button icons / d-pad glyphs | Visual diff vs original |
| Model, serial, FC oval, BIS | Match the pre-edit transcription and `label.jpg` |
| Port layout | Same count and order as the photo |
| No GPS | PIL/identify: no gps/exif on shipped JPEGs |
