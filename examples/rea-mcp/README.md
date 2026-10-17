# Reverse Engineer Anything (REA) MCP snippets

Third-party MCP from `rea-agents` (MIT, https://github.com/morluto/rea).

The pack ships a **skill snapshot** under `agent/skills/reverse-engineer-anything/`
(skill v42, package `rea-agents@6.5.0`). Installing the skill does not register
the MCP server. Copy one of these snippets, then restart the client.

Do not add Hopper/Ghidra/JADX/IDA install steps here. REA setup never installs
those engines.

## Grok Build

Merge `grok-mcp.toml.example` into `~/.grok/config.toml`.

Grok with `[compat.claude] mcps = true` also inherits a Claude `rea` server.
Prefer **one** registration so the session does not start two stdio processes.

Official refresh:

```bash
npx -y rea-agents@6.5.0 setup --client grok_build --dry-run --json
# review paths/backups, then:
npx -y rea-agents@6.5.0 setup --client grok_build --yes
```

That command also writes `~/.agents/skills/reverse-engineer-anything`.

## Claude Code

Merge `claude-mcp.json.example` into `~/.claude.json` `mcpServers`.

```bash
npx -y rea-agents@6.5.0 setup --client claude_code --dry-run --json
npx -y rea-agents@6.5.0 setup --client claude_code --yes
```
