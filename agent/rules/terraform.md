---
paths:
  - "**/*.tf"
  - "**/*.tfvars"
  - "**/terraform/**"
  - "**/opentofu/**"
---

# OpenTofu / Terraform

- Prefer `tofu` when installed; otherwise `terraform`
- `fmt` + `validate` after edits
- Lint with `tflint`; scan with `tfsec` / `checkov`
- No hardcoded secrets or account IDs — variables or data sources
- Review `plan` before suggesting apply
- Prefer JSON plan show for analysis
- Prefer `for_each` over `count` for stable addresses
- Use `moved` blocks for renames when possible
- Do not run apply/destroy/state rm from the agent unless the user explicitly runs a privileged command
