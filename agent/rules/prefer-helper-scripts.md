---
paths:
  - "**"
---

# Prefer Helper Scripts

When a host procedure is a **repeatable sequence** (pinentry, dialogs, session
dbus, PATH bootstrapping, retries around a local binary), **do not re-derive
it in the parent thought loop**. Look for a helper **before** inlining or
spawning a child to run the same steps.

**Do this first:**

1. Look on `PATH`, `{AGENT_HOME}/scripts/`, and the general pack `bin/` for a
   helper.
2. If it exists, **call it**. Do not inline the same kdialog / pinentry /
   KWin / loopback steps as a one-off compound command.
3. If the work is **more than a single command**, strongly consider writing a
   helper this turn, then call it. Copy it into the general pack `bin/` plus
   `{AGENT_HOME}/scripts/` (and `~/.local/bin`).
4. If **multiple greps** are required **and** the same bundle looks useful
   later, write a helper this turn. Router diagnostics (iptables, current
   clients, system statistics) is that shape. A one-shot verify
   (`ss -tnp | grep 11434` to check a port opened) stays on the parent —
   spawn tax exceeds the output, and a helper for a one-time check is waste.
5. If it is missing and you are about to reconstruct **3+** of those steps,
   **write the helper this turn** (same copy path), then call it.

Do not spawn a subagent only to run a short command sequence a helper should
own. A single command (`rg`, `systemctl status`, `git status`) and a single
command piped into grep stay on the parent (rule `subagents-first`). The
hook allows `ss | grep foo | grep bar`; still prefer a helper when that
pipeline is a reusable diagnostic.

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
