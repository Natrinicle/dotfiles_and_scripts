---
paths:
  - "**/toolkit.yaml"
  - "**/TOOLKIT.md"
  - "**/install.sh"
  - "**/dotfiles*/**"
  - "**/shell/bash*"
  - "**/bash_aliases.d/**"
  - "**/agent/**"
---

# README Freshness for Shareable Packs

After changing a portable package (dotfiles, agent toolkit, installable script pack), update `README.md` in the **same change set**.

Check:
1. Layout matches the tree
2. Install steps still work
3. Benefits and placeholders are accurate
4. Exclusions are listed if privacy required drops

Do not ship content that the README no longer describes.
