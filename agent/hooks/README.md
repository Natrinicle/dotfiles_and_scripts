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

## prefer-spawn-search

`PreToolUse` matcher: `grep|Grep|list_dir|LS|Glob|glob`

Injects `additionalContext` on **wide** searches (missing path, `$HOME`,
agent config roots, `**` globs). Named-file grep is silent. Does not block.
Fail-open.

On Grok Build, unknown-path search: omit `subagent_type` (cloud
general-purpose). Do not pin plugin explorers to `ollama-gemma4`.

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
