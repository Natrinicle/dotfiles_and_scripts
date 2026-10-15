---
name: server-account-audit
description: "Server companion to password-account-evidence. Extend account-protection checks to SSH keys, sudoers, disabled password auth, lastlog, and cloud IAM for server access audits."
type: knowledge
lifecycle: active
---

# Server Account Audit

Thin companion to `password-account-evidence`.

## Core reuse

Apply `password-account-evidence` for local Windows account password evidence and the `PASSWORD_EVIDENCE` block.

## Server additions

- Linux: `/etc/shadow` (password hash presence or `!`/`*`), `passwd -S`, SSH `PasswordAuthentication`, `authorized_keys`, sudoers, `lastlog`/`faillog`.
- Windows: local accounts, LSA, disabled interactive logon.
- Cloud: IAM users/roles, key-only access, unexpected local accounts on instances.
- Goal: confirm interactive password logins are disabled where expected.

## Output

Extend block:

```
PASSWORD_EVIDENCE
...core...
ssh_password_auth: enabled|disabled|unknown
unexpected_local_accounts: list or none
```

## Upstream note

Negative-evidence approach is shared.
