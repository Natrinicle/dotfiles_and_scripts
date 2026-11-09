# Visual system

Two grammars, one dark terminal surface. Combine them in `combo`.

## Surface

- Background `#101218`, chrome `#1c1f27`, text `#e6e8ee`, muted `#8b919c`
- Mono: Fira Code / FiraCode Nerd Font / DejaVu Sans Mono
- Default canvas 1200×1500. Tree-only may use 1200×980 (bootvine is 1380×980)
- `chrome: tui` for a raw console header. `chrome: window` adds traffic-light
  titlebar when the source dashboard had OS chrome

## Status colors and glyphs

| State | Glyph | Color | Meaning |
|-------|-------|-------|---------|
| waiting | `[ ]` | muted text | Not started; still pending |
| running | `[|]` | yellow `#f0d24a` | Live; show elapsed on the right after a few seconds |
| done | `[√]` | green `#7dffa3` | Finished (keep briefly, then drop from a pending-only tree) |
| failed | `[×]` | magenta `#e06090` | This unit broke; failure panel owns the log lines |
| blocked | `[\]` | dim red | Failed only because a unit it needed failed |

Stage diamonds: `◆` current, `◇` still to come, `√` reached.

Role colors on packet cards (advisor-style):

| Role | Color | Typical system |
|------|-------|----------------|
| lead | orange `#e89562` | Executor, ingress, parent |
| swarm | blue `#6ea0ff` | Fan-out workers, search |
| local | green `#7dffa3` | Cheap/local helper |
| advisor | purple `#c4b5fd` | Gate / independent checker |

## Tree grammar (bootvine aspects)

Replace a wall of logs with the units that still matter.

1. **Header** — host, system name, kernel or version; elapsed since start on
   the right.
2. **Stages** — finished stages show duration and unit count; the live stage
   ends in running. Initrd vs stage 2 is one example of a stage break, not
   the only one.
3. **Pending tree** — nest each unit under the unit waiting on it. Milestone
   targets (`*.target`, "ready", "default") open the levels. Kind and
   description columns sit to the right of the name. A single-child chain
   may fold onto one row joined by `─` when labels overflow.
4. **Hide the noise** — finished and long-waiting rows give way first when
   the tree is taller than the canvas. Count omitted units on a last line.
5. **Failure panel** — newest break first: headline (unit + why) and up to
   six last lines from that unit. Units that failed only through a
   dependency stay dimmed in the tree and stay out of the panel.
6. **Timeline** — in the leftover space below the tree: slowest finished
   units and still-running units as bars against seconds. A vertical mark
   splits stages (initrd → root, edge → app). Waiting bars are dotted.
7. **Footer census** — `done` / `running` / `waiting` / `failed`.
8. **Shutdown** — invert the tree: the target being reached is the root;
   the unit holding up the stop sits at the bottom of its branch.
9. **Overlay prompt** — a passphrase or blocking question floats over a
   dimmed tree; it is not a new log dump.

Do not copy bootvine source. This is the on-screen grammar.

## Packet grammar (advisor-style dashboard)

1. **Cards** for a handful of systems. Border and title follow `role`.
2. **Wires** — vertical for a stack, horizontal for a row. Each `talks`
   edge is a wire with a label (HTTPS, SQL, queue, spawn).
3. **Packets** — 8px dots, color = tone (`o` orange, `b` blue, `g` green,
   `p` purple, `a` amber, `r` magenta). CSS `fall` on vertical wires,
   `slide` on horizontal. `--dur` and dot count follow expected volume on
   that edge (busy pipes faster and denser; trickle slower and sparser).
   Each packet sets `--dur` inline so bake frames stay honest.
4. **Gate rail** — purple left rail. Active gate uses `class="gate active"`
   (background fill + diamond). Inactive gates stay outlined.
5. **Session log** — secondary. Four to six rows: time, tag, one line.
   The tree or the cards remain the primary picture.
6. **CLI line** — prompt + command + block cursor.

## Combo

Tree (who is waiting on whom) on top. Packet strip (who talks to whom)
under it. Timeline + failures + footer + log + CLI under that. Use this
when the ask is "data flow paths" or "flows between systems."

## Layout rules

- Prefer CSS grid and flex. Do not nudge absolute coordinates by hand
  after the first pass.
- One canvas, no scroll. If it does not fit, drop finished rows and keep
  the census.
- Verify by reading the PNG: every system name, every edge label, every
  footer count, no clipped glyphs.
