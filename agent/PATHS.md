# Path conventions

Skills use placeholders so Claude Code and Grok can share the same pack.

| Placeholder | Meaning | Typical values |
|-------------|---------|----------------|
| `{AGENT_HOME}` | Agent config root | `~/.claude`, `~/.grok` |
| `{AGENT_RULES}` | Rules directory | `{AGENT_HOME}/rules` |
| `{AGENT_SKILLS}` | Skills directory | `{AGENT_HOME}/skills` |
| `{AGENT_HOOKS}` | Hooks directory | `{AGENT_HOME}/hooks` |
| `{AGENT_SETTINGS}` | Host settings | `settings.json` / `config.toml` |
| `{MEMORY_ROOT}` | Global memory | `{AGENT_HOME}/memory` (often one symlinked tree) |
| `{PROJECT_MEMORY}` | Per-project memory | under the host's projects tree |

## Helper scripts

Install repo `bin/` to **`~/.local/bin`** (on `PATH`). Skills should call bare commands such as `morning-data-gather` or `speakr-api`, never a vendor-specific scripts directory.
