---
name: generate-ignore-list
description: >
  Scan a tree and produce ignore rules for backups or git, asking when data might be irreplaceable.
---

# Generate Ignore List

## Principles

1. Keep config and secrets material; exclude redownloadable bulk.  
2. Prefer anchored paths for top-level noise.  
3. Iterate with the user after a first pass (size surprises are normal).  

## Process

1. Walk the target; note large dirs and known cache names.  
2. Draft rules for the chosen tool (gitignore syntax vs backup tool dialect).  
3. **Ask** before excluding anything that might be original content (photos, research).  
4. Write rules to a file path; don’t rely on indented chat blocks for copy-paste.  
5. Suggest a verification command (e.g. backup dry-run or `du`).  

Never exclude credential directories by default.
