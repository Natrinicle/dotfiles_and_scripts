---
paths:
  - "**"
---

# Prefer Updates Before Workarounds

When a local tool, wrapper, or runtime fails in a way that looks like
**missing feature support** (unknown compression, unsupported format, old
library, “this version supports only …”), **check for a newer version of
that installed component before building workarounds.**

**Do this first:**

1. Identify the interceptor/wrapper (for example AppImageLauncher via
   binfmt), not only the file the user launched.
2. Check installed version vs upstream changelog/issues for the exact error.
3. Tell the user if an update likely fixes it. Do **not** install or
   upgrade without explicit approval.

**Do not jump to:** extract-and-run, rebuild, FUSE reinstall, custom
wrappers, or patching the payload until an update is ruled out.

Workarounds are fine after that check, or when the user already has the
current version.

Full incident note: `{MEMORY_ROOT}/feedback-prefer-updates-before-workarounds.md`
