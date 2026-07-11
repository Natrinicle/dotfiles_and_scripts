---
paths:
  - "**/auth/**"
  - "**/middleware/**"
  - "**/api/**"
  - "**/routes/**"
  - "**/controllers/**"
  - "**/*.tf"
  - "**/Dockerfile*"
  - "**/.github/workflows/**"
  - "**/docker-compose*.y*ml"
  - "**/ansible/**"
  - "**/playbooks/**"
---

# Security Checks

Apply when touching auth, APIs, infrastructure, or dependency surfaces.

## Input validation
- Validate and sanitize at trust boundaries.
- Prefer schema libraries (Zod, Valibot, Joi, etc.) over ad-hoc checks.
- Bound string lengths; reject unexpected fields.

## XSS and URLs
- Do not render unsanitized HTML.
- Sanitize dynamic URLs before use in navigation or embeds.

## AuthN / AuthZ
- Never hardcode secrets; use environment or a secret manager.
- Verify tokens server-side; do not trust client-decoded claims alone.
- Authorize on every sensitive operation, not only at the edge router.

## Infrastructure scans
- SAST: e.g. `semgrep --config=auto` on auth/API changes
- IaC: `tfsec` / `checkov` on Terraform/OpenTofu
- Images: `hadolint` on Dockerfiles; `trivy fs` for dependency vulns
- Secrets: `gitleaks detect` before committing sensitive trees

## Common bugs
- No shell injection: list args, never interpolate untrusted input into a shell.
- No SQL/NoSQL injection: parameterized queries or safe ODMs.
- No path traversal: allowlist bases; reject `..`.
- No SSRF: allowlist outbound hosts where practical.
