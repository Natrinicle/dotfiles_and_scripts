---
name: mempalace-recall
description: Search the memory palace before answering about past work, decisions, people, projects, or previously filed APIs/CLIs/devices/methods.
---

# MemPalace Recall

Before answering about prior decisions, people, or a named API/CLI/device
interface, call `mempalace_kg_query` (no `as_of`) then `mempalace_search`.
Skip for pure greenfield edits with no memory angle. Standing SOPs stay in
rules/skills; the palace holds history.
Rule `mempalace-file-interfaces` covers filing those interfaces after discovery.
Rule `prefer-mempalace`: palace current KG / newest `filed_at` beats a local
memory-file copy. Harness skills and rules stay on disk.
