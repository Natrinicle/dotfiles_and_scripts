---
name: package-toolkit
description: >
  Package agent toolkits or environment packs into a sanitized shareable tree.
  Abstracts personal paths and org names. Helpers belong on PATH.
---

# Package Toolkit

## Kinds

| Kind | Contents |
|------|----------|
| Agent | rules, skills, PATHS conventions |
| Environment | shell startup, aliases, `bin/` helpers |

## Abstraction

- `${HOME}`, `{MEMORY_ROOT}`, `{AGENT_HOME}` over absolute homes  
- `{company}` only as a placeholder, never a real employer name in exports  
- Role-level wording when vendor is incidental  
- Keep real CLI names when the CLI is the interface  

## Workflow

1. Inventory; drop secrets, backups, and package-manager symlinks  
2. `scripts/sanitize-copy.py` + abstraction rules  
3. `toolkit.yaml` + README (keep README fresh with content)  
4. Residual-scan for names, emails, tokens, absolute homes  

## Install contract

`toolkit.yaml`, README, preferably `install.sh` with backups.  
Scripts install to **`~/.local/bin`**, not vendor `scripts/` dirs.
