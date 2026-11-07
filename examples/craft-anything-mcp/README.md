# Craft Anything MCP snippets

Optional reconstruct engine from Craft Anything
(https://github.com/storytold/craft-anything, MIT OR Apache-2.0).
Documented as_of **v0.3.0** (early alpha). Own copy / authorized
targets only.

The reconstruct loop lives in skill `clean-room-reconstruct`. Installing
that skill does not register this MCP server. Copy one of these snippets,
then restart the client, only when you named Craft Anything.

Do not dump the Craft app suite into a skill. Do not add Hopper/Ghidra
install steps here.

## CLI

```bash
craft-anything-cli commands
craft-anything-cli mcp
craft-anything-cli rebuild <url-or-dash> "<prompt>"
craft-anything-cli doctor
```

Linux AppImage also carries the CLI: `<AppImage> --cli mcp`.

Default **clean-room** refuses tools that look inside. `--deep` is
private analysis of an own-copy. Loop: Study → Build → Check → Ready.

## Grok Build

Merge `grok-mcp.toml.example` into `~/.grok/config.toml`.

## Claude Code

Merge `claude-mcp.json.example` into `~/.claude.json` `mcpServers`.
