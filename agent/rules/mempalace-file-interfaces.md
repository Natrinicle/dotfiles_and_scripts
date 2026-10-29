---
paths:
  - "**"
---

# File discovered interfaces in MemPalace

When you learn how an **API, CLI, device, MCP server, library, or protocol**
talks, file it in MemPalace **in the same turn you recovered it**, before the
user-facing answer. Do not wait for the user to ask to save.

This includes recovered **command sequences** a later session needs to repeat
the talk: AT strings, GATT write/notify UUIDs and payload hex, UART / I2C /
SPI frames, HTTP paths, register maps, MCP tool order, host radio / iface
as-builts used to reach the device.

Palace `add_drawer` / `kg_add` is the filing step. **Commit** in this rule
means that palace write. It is not a git commit. Local-first still asks
before `git commit`, push, or server mutate.

## Same-turn gate

A scan, decompile, datasheet, or live probe that yields a new method is
unfinished until the drawer and KG facts exist. A capability or feasibility
answer that uses those methods still files them, including sequences never
executed yet.

1. Lookup (below). Skip the write only when the unique methods are already
   current KG plus the newest drawer.
2. File (below) and search-verify. 0 drawers for those method names means
   it is not filed.
3. Answer. One line with drawer id or unique phrase.

## Do not skip

A chat recap of recovered AT, GATT, UART, HTTP, or MCP sequences is not
filing. Waiting for the user to say "save this to MemPalace" is a miss.
Capability answers that quote commands still file those commands first.

Do not treat "I can file this later" as done. File before the user-facing
answer, then answer.

## Lookup (before rediscovery)

On a named interface: `mempalace_kg_query` on the tool/device, then
`mempalace_search`, **before** web search, docs scrape, `--help` harvest,
BLE scan, or decompile. Use the current drawer. Probe the live system when
the palace has no hit or `version` / firmware changed.

## File

1. `mempalace_add_drawer` with wing and room set (MCP so room is correct on
   first write). Include the template below. Env-var **names** only; no
   tokens, passwords, or cookies.
2. `mempalace_kg_add` lookup keys (object ≤ 128 chars). Locked predicates:
   `interface_kind`, `version` (single-valued), `has_method` (one triple per
   command/endpoint/UUID), `reach` (binary, base URL, BLE name). New
   concurrent methods: `kg_add`. Replacing `version` or `reach`:
   `mempalace_kg_supersede`.
3. Search-verify unique method names. 0 drawers means it is not filed.

| Kind | Typical wing / room |
|------|---------------------|
| Device, BLE, UART, firmware, registers | `personal` / `hardware` (or the project wing) |
| CLI, MCP, HTTP/gRPC API, library | `personal` / `tools` or `technical` / `tooling` |
| Product-owned API | that project's wing |

Skip one-off errors and ordinary stdlib. `add_drawer` is for these
interface cards only. Directory mines use CLI
`mempalace mine DIR --daemon` (recipe:
`{MEMORY_ROOT}/feedback-mempalace-mine-directory.md`). Timeline:
`mempalace-timeline-supersede`. Session continuity that would be lost to
parent compact: rule `mempalace-compact-filing` (the compact summary is
not filing).

```text
# Interface: {name}
kind: api | cli | device | mcp | library | protocol
as_of: YYYY-MM-DD
status: current
version: …

## Reach
binary / base URL / BLE name / UART / host iface …

## Methods
- NAME — args / UUID / path / register / AT or hex payload

## Notes
gotchas; env var names only; executed vs recovered-only

## Source
docs URL, package version, capture date
```
