---
name: tofu-plan-review
description: Parallel review of OpenTofu/Terraform plans for risk, security, and drift.
---

# Tofu Plan Review

Prefer `tofu show -json` (or terraform equivalent). Review through concurrent lenses:

1. Destroy/replace risk and blast radius  
2. Security (IAM, network exposure, encryption)  
3. Drift vs intended architecture  

Summarize add/change/destroy counts, critical items, and safer alternatives.
Never apply from this skill.
