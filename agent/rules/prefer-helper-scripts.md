---
paths:
  - "**"
---

# Prefer Helper Scripts

When a host procedure is a **repeatable sequence** (pinentry, dialogs, session
dbus, PATH bootstrapping, retries around a local binary), **do not re-derive
it in the parent thought loop**.

**Do this first:**

1. Look on `PATH`, `{AGENT_HOME}/scripts/`, and the general pack `bin/` for a
   helper.
2. If it exists, **call it**. Do not inline the same kdialog / pinentry /
   KWin / loopback steps as a one-off compound command.
3. If it is missing and you are about to reconstruct **3+** of those steps,
   **write the helper this turn**, copy it into the general pack `bin/` plus
   `{AGENT_HOME}/scripts/` (and `~/.local/bin`), then call it.

## Git GPG commits

Signed `git commit`: `gpg-git-commit -C REPO --title STR -- git-commit-args`.
Never `--no-gpg-sign`. Never paste a passphrase into the transcript.

## Do not

- Spend thought cycles rediscovering session `DISPLAY` / `WAYLAND_DISPLAY` /
  `DBUS_SESSION_BUS_ADDRESS` for pinentry.
- Inline `kdialog --password` plus a throwaway `/tmp` gpg wrapper.
- Skip signing because pinentry timed out.

Landing still follows **ask-before-remote-actions**. Pack copy follows
**skill-toolkit-sync**.
