---
paths:
  - "**"
---

# File discovered interfaces in MemPalace

When you learn how an **API, CLI, device, MCP server, library, or protocol**
talks (endpoints, flags, GATT UUIDs, UART/I2C/SPI framing, register maps,
method names), file it in MemPalace so later sessions query the palace for
those interfaces and methods.

## Lookup (before rediscovery)

On a named interface: `mempalace_kg_query` on the tool/device, then
`mempalace_search`, **before** web search, docs scrape, `--help` harvest,
BLE scan, or decompile. Use the current drawer. Probe the live system when
the palace has no hit or `version` / firmware changed.

## File (after discovery)

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

Skip one-off errors and ordinary stdlib. Mine-via-directory recipe:
`{MEMORY_ROOT}/feedback-mempalace-mine-directory.md`. Timeline:
`mempalace-timeline-supersede`.

```text
# Interface: {name}
kind: api | cli | device | mcp | library | protocol
as_of: YYYY-MM-DD
status: current
version: …

## Reach
binary / base URL / BLE name / UART …

## Methods
- NAME — args / UUID / path / register

## Notes
gotchas; env var names only

## Source
docs URL, package version, capture date
```
