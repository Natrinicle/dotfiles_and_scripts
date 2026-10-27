# Local identity subagent prompt

Parent fills `{BUNDLE_PATH}` after:

```bash
python3 scripts/identity-subagent-scan.py --root PACK_ROOT --out /tmp/identity-bundle.md
```

Prefer `identity-subagent-scan.py --ollama` (direct Ollama `/api/generate`,
model `gemma4`). Spawn `local-extract` / `explore` (omit `model`) only when
Ollama is down, and pass **only** this prompt plus the bundle. Do not spawn
`general-purpose`. Read-only. Do not edit pack files.

## Task

Read `{BUNDLE_PATH}` (and this prompt). Each bullet is a heuristic leftover
span. Classify it. Return **only** the JSON object below.

Keep public vendor-locked interface names. Example that stays:

> When accessing AWS, use IAM roles.

Also keep GitHub, Docker, Traefik, Flipper, Kubernetes, and any name already
listed in the pack README **Vendor-specific bits** table.

Replace person names, employer/customer names, personal shops/domains, and
other leftover PII that is not a public tool/cloud/OSS interface.

Documented fake examples used to describe the example denylist (`Alice Example`,
`Acme Corp`) stay.

Placeholders (`{company}`, `{subject}`, `{user}`, `${HOME}`) stay.

## Output

```json
{
  "hits": [
    {
      "path": "relative/file.md",
      "line": 1,
      "kind": "person|employer|personal-domain|other-pii",
      "span": "ExampleEmployerName",
      "replace_with": "{company}"
    }
  ],
  "kept_vendor": [
    {
      "path": "README.md",
      "span": "AWS",
      "reason": "vendor-locked public cloud"
    }
  ]
}
```

Empty `hits` if every span is vendor-locked or a placeholder. Do not invent
paths. Do not quote real host denylist tokens in the report if a span was
already `[redacted]`.
