---
name: session-tunes
description: Quiet evolving RTTTL flock while Grok/Claude think, occasional 70s computer-room analog beeps, unique stings on needed input or failure. Use when session soundtrack, chiptune, ringtone codes, Electric Sheep audio, busy/idle audio, or local Ollama tone generation comes up.
---

# Session Tunes

A user systemd player runs an Electric Sheep-style flock of quiet RTTTL clips while a Grok or Claude session is thinking. Clips crossfade, never the same genome twice in a row. A 70s computer-room analog beep train (TechMoan 38:36 sting: 1650 → 1890 → 2025 Hz boop, then 1495/2740 Hz doots) shows up on about 15% of clips. Alerts are unique flock stings, slightly louder and more urgent by type.

The skill tree ships original short seeds. Drop extra `.rtttl` files into `~/.local/share/session-tunes/library/` for more variety. The flock mutates those plus local Ollama `gemma4` motifs every 15 minutes. Keep downloaded ringtones out of this skill tree.

Keep background far below calls/media. PCM: `busy_amplitude = 0.0045` (triangle RTTTL), `modem_amplitude = 0.0051`, `alert_amplitude = 0.0106`, `error_amplitude = 0.0138`. paplay uses `media.role=abstract`.

## Layout

| Path | Role |
|------|------|
| `{AGENT_HOME}/skills/session-tunes/scripts/` | parser, player, hooks, daemon, ctl |
| `{AGENT_HOME}/skills/session-tunes/library/` | seed `.rtttl` (original compositions) |
| `~/.config/session-tunes/config.toml` | volumes, Ollama, timers |
| `~/.config/session-tunes/mute` | mute flag (presence = silent) |
| `~/.local/share/session-tunes/library/` | extra + generated RTTTL (backupable) |
| `~/.local/share/session-tunes/flock/` | evolving genomes |
| `~/.cache/session-tunes/` | state.json (expendable) |

## States

| State | Source | Audio |
|-------|--------|-------|
| `busy` | `UserPromptSubmit`, or C fallback (session file growth / `systemd-inhibit` "agent turn in progress") | evolving RTTTL flock, modem on ~15% of clips |
| `attention` | `Notification` `permission_prompt`; Grok `approval_required` | one sting, then hold silent ~12s |
| `error` | `StopFailure`; Grok `agent_error` | one falling sting |
| `idle` | `Stop`, `StopCancelled`, `SessionEnd`, `idle_prompt` | silence |

Skip `PreToolUse` (blocking). After an attention sting, C fallback (transcript mtime / inhibit) restores busy once the hold expires. Ignore `subagentType` events; the parent session drives the tune.

Shared lifecycle hooks live only in `~/.claude/settings.json` so Grok (`compat.claude hooks = true`) does not double-fire. Grok-only events (`StopFailure`, `StopCancelled`) live in `~/.grok/hooks/session-tunes.json`.

## Commands

```bash
session-tunes install --enable
session-tunes status
session-tunes mute
session-tunes unmute
session-tunes test busy    # unique flock clip; also alert|error|modem
session-tunes generate-now
systemctl --user status session-tunes.service
```

`install.sh --agent --bin` copies the skill and `bin/session-tunes`. Then `session-tunes install --enable` installs the user unit.

## Volumes

Edit `~/.config/session-tunes/config.toml`. Default `thinking_sound = peppy` with `modem_chance = 0.15`. Flock evolves every `generate_interval_s = 900` (15 min), batch of 10. Raise `busy_amplitude` only if inaudible. Do not switch `media.role` to `event` or `notify` (those duck calls).

## Anti-patterns

- Putting the same `UserPromptSubmit`/`Stop` hook in both `~/.grok/hooks/` and Claude settings
- Calling LiteLLM `:4000` for generation (use native Ollama `/api/generate`)
- Copying downloaded identifiable RTTTL into a shareable toolkit (keep those under `~/.local/share`)
- paplay default role (ducks media) or PCM near 0.2 (disrupts calls)
