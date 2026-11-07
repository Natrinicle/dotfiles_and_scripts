# Agent hooks

Command hooks for Claude Code and Grok (`compat.claude hooks = true`).
Install copies scripts to `{AGENT_HOME}/hooks/`. Registration stays in host
`settings.json` so Grok does not double-fire a `~/.grok/hooks/` copy.

## spawn-subagent-local-pin

`PreToolUse` matcher: `spawn_subagent|Task`

Grok `[subagents.models]` matches the exact `subagent_type`. Native
explore-class names (`explore`, `code-explorer`, `local-search`, …) that omit
`model` are pinned to the host T0 local id.

Plugin ids such as `feature-dev:code-explorer` are **not** rewritten to
`ollama-gemma4`. Grok's gemma4 model entry is a 16K window; plugin explore
inject is ~24K, so a local pin overflows before the first tool. Those types
inherit the parent cloud model. This hook:

- Rewrites an omitted `model` on **native** explore-class types to the host T0
  local id
- Warns (no rewrite) on plugin explore types
- Leaves explicit cloud `model`, reviewers, and `general-purpose` alone

Register (do not also add under `~/.grok/hooks/`):

```json
{
  "matcher": "spawn_subagent|Task",
  "hooks": [
    {
      "type": "command",
      "command": "python3 {AGENT_HOME}/hooks/spawn-subagent-local-pin.py",
      "timeout": 5
    }
  ]
}
```

Restart the session after changing hook registration. Fail-open on errors.

## retarget-grok-plugin-symlinks

`SessionStart` (and `sync-from-claude.sh --verbose`).

`claude plugin update` replaces version dirs (including `unknown`) and deletes
the old Claude cache folder. Grok `~/.grok/plugins/<name>` symlinks go
dangling; plugin hooks then fail with `its plugin folder ... is gone`.

This hook retargets those symlinks from `installed_plugins.json` `installPath`.
Quiet when already correct. Prints healed names on SessionStart. Never
replaces a native (non-symlink) dest. Fail-open.

Register once in host `settings.json` (do not also add under `~/.grok/hooks/`):

```json
{
  "hooks": [
    {
      "type": "command",
      "command": "python3 {AGENT_HOME}/hooks/retarget-grok-plugin-symlinks.py",
      "timeout": 10
    }
  ]
}
```

## control-plane-exposure

`PreToolUse` matcher:
`Bash|bash|run_terminal_command|Write|write|Edit|StrReplace`

`UserPromptSubmit` (no matcher) injects the spin-up evidence gate.

**Denies** `kubeadm init` / `join` (not `kubeadm init phase certs`),
k3s/rke2 server installers, `ufw allow` / `iptables ACCEPT` / `0.0.0.0/0`
on API `:6443`, kubelet `:10250`, etcd `:2379`/`:2380`,
controller-manager `:10257`, scheduler `:10259`, Docker `:2375`/`:2376`.
DROP/REJECT of those ports, probes, and `kubectl` stay allowed. Fail-open.
Escape (user must name it): `SYSTEM_SECURITY_ALLOW_WAN_CONTROL_PLANE=1`.

Rule `system-security` + skill `k8s-control-plane-vpn`. Hookify
`.claude/hookify.*.local.md` is a second deny (project CWD). Register
once in host `settings.json` (do not also add under `~/.grok/hooks/`):

```json
{
  "matcher": "Bash|bash|run_terminal_command|Write|write|Edit|StrReplace",
  "hooks": [
    {
      "type": "command",
      "command": "python3 {AGENT_HOME}/hooks/control-plane-exposure.py",
      "timeout": 5
    }
  ]
}
```

Restart the session after changing hook registration.

## prefer-spawn-search

`PreToolUse` matcher:
`grep|Grep|list_dir|LS|Glob|glob|Bash|bash|run_terminal_command`

**Denies** forest and multi-location search (missing path, `$HOME` / `/` /
`~/repos`, unscoped `**` glob, two+ directory operands, unpiped shell
`rg`/`grep`/`find` with no path). A single `rg` / `grep` / `find` /
`list_dir` of **one** tree (including a git repo root) stays allowed.
A grep-family filter of stdin (`ss | grep 11434`, `git show … | grep`)
stays allowed. Named-file grep and `git status` stay allowed. Fail-open.
Escape: `SUBAGENTS_FIRST_ALLOW_PARENT_SEARCH=1`.

The deny reason tells the parent: one command stays here; spawn for
multi-location search, software install with config+units, or large extract.
Several independent units → skill `agent-graphs`. Bug hunt stays
`find-patch-loop`. One-shot verify (did this open the port) stays on the
parent. Reusable multi-grep diagnostics (router iptables/clients/stats)
→ helper script.

On Grok Build, multi-location unknown-path search: omit `subagent_type`
(cloud general-purpose). Do not pin plugin explorers to `ollama-gemma4`.

## mempalace-postcompact-index

`PostCompact` (matcher omitted: `manual` and `auto`)

Grok writes full turn text to session `compaction/segment_*.md`. Mining
those files dumps skill-list noise. This hook stages only `INDEX.md`
plus a session pointer, then `mempalace mine DIR --daemon --background`.
The model still files necessary pieces per rule `mempalace-compact-filing`.
Fail-open. Skip when INDEX is unchanged (sha256 marker). Do not also
register under `~/.grok/hooks/` (Claude settings already fire on Grok).

Register:

```json
{
  "hooks": [
    {
      "type": "command",
      "command": "python3 {AGENT_HOME}/hooks/mempalace-postcompact-index.py",
      "timeout": 20
    }
  ]
}
```

Optional env: `MEMPALACE_COMPACT_WING` (default `personal`).
