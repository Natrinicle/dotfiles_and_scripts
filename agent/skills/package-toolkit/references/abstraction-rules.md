# Abstraction rules

## Paths
Map absolute homes to `${HOME}` or `~/…`. Prefer `$USER` over literal logins.

## Identity
Replace names, emails, and personal domains with `{user}`, `{full_name}`, `{personal_domain}`.

## Organization
Replace employer product names with `{company}` / `{Company}` unless the public tool name *is* the interface.

## Messaging
When the skill is about chat in general, say IM/messaging; keep a vendor CLI name only when calling that CLI.

## Secrets
Never pack secret values. Use env vars or `{SECRET_NAME}` plus an example env file.
