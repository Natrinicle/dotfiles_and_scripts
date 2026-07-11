---
paths:
  - "**/*.yml"
  - "**/*.yaml"
  - "**/ansible/**"
  - "**/playbooks/**"
  - "**/roles/**"
---

# Ansible

- Every task needs a descriptive `name:`
- Use `become: true` on tasks that need privilege, not only play-level become
- Prefer FQCN modules (`ansible.builtin.copy`, …)
- Prefer modules over `shell`/`command`; if shell is required, set `changed_when`
- Prefer `template` when content is variable
- Quote vars in `when:`; avoid Jinja inside `when`
- Defaults in `defaults/`, constants in `vars/`, secrets in vault
- Keep tasks idempotent; use `creates`/`removes` for shell when possible
- Syntax-check playbooks before commit; run `ansible-lint` when available
