---
name: meld-style-diff
description: Use when presenting change comparisons, side-by-side diffs, Meld-style output, YAML/JSON structured diffs, dyff reports, or a reviewer prefers Meld over GitHub diffs
---

# Meld-style diffs

Present change comparisons as aligned two-pane Meld output. YAML and JSON also get a [dyff](https://github.com/homeport/dyff) path report. GitHub unified `+/-` hunks are the fallback when the user asked for a patch they can apply.

## When to use

- Side-by-side diff, Meld-style comparison, or `/meld-style-diff`
- YAML, JSON, Helm values, Kubernetes manifests, or other structured docs
- A reviewer finds GitHub unified diffs hard to read
- Converting a pasted unified / GitHub patch into a two-pane view
- Showing a proposed edit, `git diff`, or two file versions

**Use unified `diff` / `git apply` patches only when the user asked for a patch file.**

## Visual language

| GitHub unified | Meld style | dyff (YAML/JSON) |
|----------------|------------|------------------|
| One column, `---` / `+++` / `@@` hunks | Two panes, original left, new right | Compact path report (`spec.replicas`) |
| `-` red, `+` green, context uncolored | Green insert, red delete, blue replace | Added / removed / changed values |
| Inserts and deletes are sequential | Blank rows pad the other pane | Key reorder is a structural change |
| Optional word-diff | Intra-line highlights in replace chunks | Ignores cosmetic YAML flow vs block when equivalent |

Do not invent GitHub-style fences (```diff, `@@`, leading `+/-` as the primary view). Do not pass `dyff -o github`.

## Run the script

```bash
BIN="${AGENT_SKILLS:-$HOME/.claude/skills}/meld-style-diff/scripts/meld_style_diff.py"
python3 "$BIN" LEFT RIGHT --format html --open
python3 "$BIN" --left-text $'old\n' --right-text $'new\n' --left-label before --right-label after --format html --open
python3 "$BIN" --git HEAD --path path/to/file --format html --open
python3 "$BIN" --from-unified patch.diff --format html --open   # `-` = stdin
```

`--git-range A B`. `--format text` for chat, `ansi` for a TTY. `--dark`. `--dyff auto|always|never` (default `auto`: both sides YAML/JSON). YAML/JSON auto-run dyff when `dyff` is on PATH. `--from-unified` rebuilds only the hunk lines present in the patch, not the rest of the file.

The script prints the HTML path on its own line. Repeat that path with no leading spaces so it stays copyable.

If `dyff` is missing, Meld panes still render and stderr says so. Install with `go install github.com/homeport/dyff/cmd/dyff@latest` (do not install unless asked).

## How to present

1. Run the script. Do not hand-draw the panes or a dyff report.
2. Open the HTML for the human (browser tools or `--open`).
3. In chat, give the path plus the stderr summary (`N file(s), M change chunks`).
4. For YAML/JSON, lead with the dyff path report, then the Meld panes.
5. If the surface is text-only (Slack, a ticket), use `--format text`.
6. If `meld` is on PATH and the user wants the real GUI, `meld LEFT RIGHT` is the native tool. Still generate HTML when the GUI cannot be shared.

## Decision rules

- Default format is HTML with `--open` when a human is reviewing.
- YAML/JSON (extension or sniff): dyff **and** Meld. Source (`.py`, `.md`, …): Meld only.
- Multiple files: one `--path` per file, or omit `--path` on `--git` to take every changed path.
- Binary files (NUL in the first 8KiB): skip and say so on stderr. `--git` without `--path` still lists them as skipped.
- Apply-able patch requested: emit unified diff **in addition to** the Meld view, labeled as the patch.

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Pasting a ```diff unified hunk as the comparison | Run the script; show panes |
| Line-diff only on Helm/K8s YAML | Let `--dyff auto` run; show the path report first |
| `dyff -o github` / GitHub PR UI | Human dyff report, never GitHub style |
| Markdown before/after tables that do not align | Use the script's text format |
| Showing only the new file | Left pane is the original |
| Collapsing to `+`/`-` because the change is "small" | One-line replaces still get a blue replace row |

## Verify

```bash
python3 "${AGENT_SKILLS:-$HOME/.claude/skills}/meld-style-diff/scripts/test_meld_style_diff.py"
```
