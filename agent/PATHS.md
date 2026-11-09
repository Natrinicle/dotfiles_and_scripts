# Path conventions

Skills use placeholders so Claude Code and Grok can share the same pack.

| Placeholder | Meaning | Typical values |
|-------------|---------|----------------|
| `{AGENT_HOME}` | Agent config root | `~/.claude`, `~/.grok` |
| `{AGENT_RULES}` | Rules directory | `{AGENT_HOME}/rules` |
| `{AGENT_SKILLS}` | Skills directory | `{AGENT_HOME}/skills` |
| `{AGENT_AGENTS}` | Persona / subagent prompts | `{AGENT_HOME}/agents` |
| `{AGENT_RESOURCES}` | Shared checklists / standards | `{AGENT_HOME}/resources` |
| `{AGENT_HOOKS}` | Hooks directory | `{AGENT_HOME}/hooks` (see `agent/hooks/README.md`) |
| `{AGENT_SETTINGS}` | Host settings | `settings.json` / `config.toml` |
| `{MEMORY_ROOT}` | Global memory | `{AGENT_HOME}/memory` (often one symlinked tree) |
| `{PROJECT_MEMORY}` | Per-project memory | under the host's projects tree |

## Helper scripts

Install repo `bin/` to **`~/.local/bin`** (on `PATH`) and repo `lib/` to **`~/.local/lib`** (helpers, off PATH). Skills and agents should call bare commands such as `adf-ocr`, `morning-data-gather`, `speakr-api`, `rperks-activate`, `find-patch-queue`, `gpg-git-commit`, `employer-parent-model`, or `employer-grok`, never a vendor-specific scripts directory. Signed git commits use `gpg-git-commit` (rule `prefer-helper-scripts`). Employer-tree parent model: `employer-parent-model` / `employer-grok` (example `examples/employer-parent-model.env.example`).
