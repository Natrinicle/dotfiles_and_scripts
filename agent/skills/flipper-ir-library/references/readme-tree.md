# README tree

Every directory under `Infrared/` that contains units (or other directories)
has a `README.md`. The tree is a menu: root → type → brand → model. A click
must never 404.

## Files

| Path | Contents |
|------|----------|
| Pack `README.md` | How to copy `.ir` to the Flipper; link to `Infrared/` |
| `Infrared/README.md` | Table of device **types** |
| `Infrared/<Type>/README.md` | Table of **brands** |
| `Infrared/<Type>/<Brand>/README.md` | Table of **models** |
| `Infrared/<Type>/<Brand>/<Model>/README.md` | Photos, IDs, button map, protocol, encode script |

Create a missing ancestor README in the same change as the new unit.

## Index table shape

```markdown
| Name | Path | Notes |
|------|------|-------|
| HVAC | `HVAC/` | Ceiling cassettes, splits |
```

Child links are **relative** to that README. Spaces in a path: `Air%20V/`.

## Unit README

- Photos first (remote, then unit views, then `label.jpg` if present).
- Identification table: brand, model, serial, printed FC oval, FCC **grant**
  ID, BIS/other, power. Note when a grant ID is not printed as `FCC ID: …`.
- Flipper file name and whether it is parsed or raw.
- Button map: remote control → Flipper `name:` → command or payload.
- Protocol in one short subsection. If raw/state-based, point at `encode_*.py`
  and say Flipper will not send this as NEC.
- Mark synthesized buttons vs Flipper learns.
- Do not advertise defects the user asked to hide from photos.

## After any path change

Rename, move, or delete of a folder or README:

1. `rg -n '\]\([^)]+\)' --glob '*.md'` from the pack root.
2. Update every link that still names the old path (root table, type, brand,
   sibling units).
3. Run `scripts/check_readme_links.py` from the pack root.
4. Do not finish while it reports missing targets.

A “just this folder” edit that leaves `Infrared/README.md` pointing at the old
name is a 404. Fix ancestors in the same change.

## Pack root README

Keep the Flipper copy instructions here. Link `[Infrared](Infrared/)` as the
catalog. A short unit table at root is optional; if present it must use the
same paths as `Infrared/README.md` (one move updates both).
