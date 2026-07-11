---
paths:
  - "**/Chart.yaml"
  - "**/values*.yaml"
  - "**/templates/**"
  - "**/helm-charts/**"
---

# Helm & Kubernetes

- Run `yamllint` (relaxed is fine) on YAML you edit.
- Run `hadolint` on Dockerfiles.
- Pin image tags; never ship `latest` in production charts.
- Render charts before commit: `helm template . --debug` (or project equivalent).
- Prefer non-root, read-only root filesystem, and dropped capabilities in pod specs.
- Lint rendered manifests with `kube-linter` when available.
- Document every `values.yaml` key with a short comment.
