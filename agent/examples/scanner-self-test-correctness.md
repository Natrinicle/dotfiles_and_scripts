# Scanner / CI self-test correctness (any repo)

as_of: 2026-10-14
status: current
SUPERSEDES: “generate a random-looking secret” canaries; unsigned `curl | sudo` CLI installs

**Trigger:** writing or reviewing gitleaks canaries, `.gitleaks.toml`, CI installs of gitleaks/hadolint, or any scanner self-test. Apply in every repo.

Palace: `kg_query` `gitleaks` / `hadolint` (no wing). Search wings `technical` + `personal`: `gitleaks AWS canary A-Z2-7 sha256sum Twilio SID`.

Match the **scanner's charset**, not “looks like a key”. A mixed any-nonzero self-test lets one live rule hide a dead one.

## Charsets (gitleaks default rules)

| Secret | Prefix | Suffix charset | Length | Notes |
|--------|--------|----------------|--------|-------|
| AWS access key id | `AKIA` | **`A-Z2-7`** (base32) | 16 | Digits `0,1,8,9` never appear. `A-Z0-9` fires ~1/6 runs. |
| GitHub PAT | `ghp_` | `A-Za-z0-9` | 36 | Still in defaults. |
| Twilio Account SID | `AC` | `[0-9a-fA-F]` | 32 | **Not** in default rules (tokens/SK keys are). Custom rule required. |

### Generating the suffix

- AWS / `ghp_`: `openssl rand 128 \| base64 \| tr -dc '<charset>' \| head -c N` (32 random bytes is too few after `tr` for a 36-char `ghp_`).
- Hex SID: **`openssl rand -hex 16`** (exactly 32 hex). Do **not** `tr -dc 'a-f0-9'` from 32 random bytes (~11 hex chars expected).

### Isolation

Run a **separate** `gitleaks detect` per rule family (AWS, `ghp_`, SID). A single canary file with one `if detect; then fail; fi` passes if only `ghp_` still fires.

Custom Twilio rule:

```toml
[[rules]]
id = "twilio-account-sid"
description = "Twilio Account SID (AC + 32 hex), bare or assigned"
regex = '''\bAC[0-9a-fA-F]{32}\b'''
keywords = ["ac"]
```

Canaries: env-assigned `TWILIO_ACCOUNT_SID=AC…` **and** a bare `AC…` line.

## CI binary install (gitleaks, hadolint, same pattern)

1. `curl -sSfL` the release **asset** into `mktemp -d` (not a pipe into `sudo`).
2. `echo '<published-sha256>  <file>' \| sha256sum -c -`
3. Then `sudo tar` / `sudo install`.

Pin the digest **in git**. Fetching `checksums.txt` from the same unsigned release is weaker.

hadolint asset is **`hadolint-linux-x86_64`** (lowercase). `hadolint-Linux-x86_64` is stale.

hadolint 2.15.1 default `--failure-threshold` is **info**. Named `USER` trips DL3066 (info) and fails CI. Use `--failure-threshold warning` so warning/error stay red.

Hook `rev:` and CI CLI version must match. Local PATH binary may be older; version-match a canary against the pinned tarball.

## Related (already standing)

- Local gitleaks hook `--staged` is a no-op on a fresh CI checkout → CI must `gitleaks detect`.
- `failed to scan` is red. Empty range is not a pass.
- No empty `[allowlist]`. `pipefail` on detect.

Provenance: 2026-10-14 review of a gitleaks/hadolint CI workflow. Apply everywhere those tools appear.
