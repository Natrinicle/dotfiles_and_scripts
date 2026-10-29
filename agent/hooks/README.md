# Agent hooks

Command hooks for Claude Code and Grok (`compat.claude hooks = true`).
Install copies scripts to `{AGENT_HOME}/hooks/`. Registration stays in host
`settings.json` so Grok does not double-fire a `~/.grok/hooks/` copy.

## spawn-subagent-local-pin

`PreToolUse` matcher: `spawn_subagent|Task`

Grok `[subagents.models]` matches the exact `subagent_type`. Plugin ids such
as `feature-dev:code-explorer` miss a `code-explorer` pin and inherit the
parent cloud model. This hook:

- Rewrites an omitted `model` on explore-class types to the suffix pin or the
  host T0 local id
- Warns the parent via `additionalContext`
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
