# shrink-anything MCP snippets

Optional MCP from shrink-anything (https://github.com/EL4CTEO/shrink-anything, MIT).
Documented as_of **v0.1.0**. Own-tree / authorized targets only.

The cut loop lives in skill `shrink-anything`. Installing that skill does
not register this MCP server. Copy one of these snippets, then restart the
client, only when you named shrink-anything MCP.

Requires `shrink-anything` on PATH (`cargo install shrink-anything` or
`npm i -g @el4cteo/shrink-anything`).

Eight tools: `shrink_scan`, `shrink_cut`, `shrink_task`, `shrink_verify`,
`shrink_undo`, `shrink_report`, `shrink_weigh`, `shrink_status`.

## CLI

```bash
shrink-anything doctor
shrink-anything scan
shrink-anything cut -- npm test
shrink-anything go --agent claude -- npm test
shrink-anything mcp
```

## Grok Build

Merge `grok-mcp.toml.example` into `~/.grok/config.toml`.

## Claude Code

Merge `claude-mcp.json.example` into `~/.claude.json` `mcpServers`.
