# Abstraction rules for toolkit packaging

## Path abstraction

| Source form | Pack form |
|-------------|-----------|
| `/home/<user>/...` | `${HOME}/...` or `~/...` |
| `/Users/<user>/...` | `${HOME}/...` |
| Explicit username in path | `$USER` or `{user}` |
| Machine-specific host | `{default_host}` or env var |

Prefer `${HOME}` in shell that will be sourced; `~` is fine in docs.

## Identity abstraction

| Source | Pack form |
|--------|-----------|
| Full name | `{full_name}` or omit |
| Login / GitHub handle | `{user}` / `$USER` |
| Email | `{user}@{company_domain}` |
| Personal domain | `{personal_domain}` |
| Case-party / subject name | `{subject}` / `{account}` — never a real person in pack skills |

## Organization abstraction

| Source | Pack form |
|--------|-----------|
| Employer / customer name in prose | `{company}` |
| Company DNS / LDAP host | `{company_ldap_host}`, `{company_domain}` |
| Internal product names (when not the tool name) | `{product}` or role description |

**Exception:** Keep public open-source project names (`git`, `docker`, `yt-dlp`).

## Messaging / SaaS abstraction

| Source | Pack form |
|--------|-----------|
| Slack / Teams / Discord (when role is generic chat) | IM / messaging workspace |
| Jira / Linear (when role is issue tracker) | issue tracker |
| Specific channel IDs, team IDs | `{workspace_id}`, omit, or example |

When the skill *must* call a vendor CLI (`gh`, `slack`), keep the CLI name and
abstract only org/channel identifiers.

## Browser / local profile abstraction

| Source | Pack form |
|--------|-----------|
| `firefox:~/.../abcd.default-release` | `firefox:~/.mozilla/firefox/{profile}` |
| Machine-local cookies path | placeholder + README note |

## Secrets

Never copy values. Replace with:

- `${VAR}` already in the source, or
- `{SECRET_NAME}` plus a line in `config/local.example.env`

## File naming in the package

- Prefer portable names: `bash_aliases` not `.bash_aliases` inside the tree
  (dotfiles become dots again at install time via `install.sh`).
- Keep category files for aliases.d (`git`, `network`, …).
- Put employer-specific leftovers under `examples/` with `.example` suffix.


## Fixtures and self-tests

Invent **synthetic** examples from scratch. Do not paste real OCR, bank/HSA
statements, credit-union mailers, barcodes, or lightly masked copies of them.

| Need | Pack form |
|------|-----------|
| Account / member number in a test | Obviously fake digits (all same, `1234567890`, or leading `0000`) |
| Mail barcode / IMB-like id | Demo prefix `9ZZ` / `9SYN` / `9TEST` / `9DEMO` / `9SAMPLE` / `9FAKE` |
| Person or street in a mailer sample | Fictional (`Sampleton Resident`, `{subject}`) |
| Issuer name in a classifier test | Fictional brand or public vendor you already document |

Keep public interface/vendor names (`kubectl`, GitHub, AWS). Residual scan flags
non-synthetic account numbers and non-allowlisted IMB-like tokens in the tree.
Never commit host denylist tokens or the original sensitive strings into tests,
docs, or example YAML.
