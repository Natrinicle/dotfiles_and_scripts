---
name: kopia-backup
description: >
  Keep backup include/exclude policy correct when paths under home or repos change.
---

# Backup Path Hygiene

When creating, moving, or deleting directories under `$HOME` or a repos tree—or when
adding tools that drop large caches—update the backup tool’s ignore rules (Kopia,
restic, borg, …).

## Keep

- Config and dotfiles you maintain  
- Keys and credential stores (small, painful to lose)  
- User-authored scripts, agent skills, memory you care about  
- Project source that is not redownloadable  

## Exclude

- Package caches (npm, pip, cargo target, …)  
- Browser caches, trash, VMs, container image stores  
- Re-downloadable toolchains  
- Huge media corpora unless the user opts in  

## Process

1. Identify new paths from the change.  
2. Classify keep vs exclude; **ask** when unsure if data is unique.  
3. Patch the ignore file; avoid excluding entire `.ssh` / `.gnupg` trees.  
4. Optionally verify with a dry-run / size estimate.  

Do not print multi-line ignore rules with leading indentation in chat if the user
needs to copy them — write a file and give the path.
