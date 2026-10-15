---
name: software-install-dating
description: "Establish true software installation date using Program Files folder creation time, update installer files with version numbers, and published version history. Use when a probable-cause statement or examiner claims a specific install date (e.g. LimeWire) that may be contradicted by artifacts; chain into expert reports."
type: knowledge
lifecycle: active
---

# Software Install Dating

Determine the actual installation timeframe of an application and refute incorrect claimed dates.

## Core Artifacts

- Creation date of the program’s folder under `Program Files` (or `Program Files (x86)`)
- Presence and dates of update installer executables (often in a subfolder such as `.NetworkShare` or `updates`)
- Version numbers embedded in update filenames
- Corroboration against publicly published version release dates

## Analysis Steps

1. Locate the application folder and record its Created timestamp.
2. List any update or patch installers and their Created/Modified dates.
3. Extract version numbers from filenames.
4. Compare against known version history (oldest update present implies the base version was earlier).
5. Note the most recent update and whether it falls outside a claimed relevant period.
6. Flag any claimed install date that post-dates the folder creation or earliest update.

## Output Format (for chaining)

```
INSTALL_DATING
application: "..."
folder_created: YYYY-MM-DD HH:MM:SS
earliest_update: YYYY-MM-DD (version)
claimed_install_date: YYYY-MM-DD or none
actual_install_window: "on or before YYYY-MM-DD"
contradicts_claim: true|false
notes: short bullets
```

## Reference

See `references/limewire-example.md` for the 5 Jul 2007 vs claimed 9 Oct 2008 case.

## Companions

- `server-package-install-dating`

Server-admin thin companions exist and should be preferred when the context is operational rather than purely forensic. When updating this skill, verify compatibility with all companions and other callers; split only if needs have diverged, with a convergence plan.
