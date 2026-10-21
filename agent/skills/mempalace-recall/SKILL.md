---
name: mempalace-recall
description: Search the memory palace before answering about past work, decisions, people, projects, or previously filed APIs/CLIs/devices/methods.
---

# MemPalace Recall

Before answering about prior decisions, people, or a named API/CLI/device
interface, call `mempalace_kg_query` (no `as_of`) then `mempalace_search`.
Skip for pure greenfield edits with no memory angle. Standing SOPs stay in
rules/skills; the palace holds history.
Rule `mempalace-file-interfaces` files recovered command sequences the same turn they are found.
Rule `prefer-mempalace`: palace current KG / newest `filed_at` beats a local
memory-file copy. Harness skills and rules stay on disk.
Lazy-load triggers (rule `lazy-load-data`) are recall too: query the
palace with the listed entity/search. Do not also read a markdown copy
of a filed as-built. Empty hit → widen once, then a disk fallback only
if that rule still lists a file that exists. Empty palace ≠ invent.
