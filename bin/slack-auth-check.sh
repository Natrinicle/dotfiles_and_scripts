#!/usr/bin/env bash
# Probe Slack session credentials used by local scrapers.
# Prints: SLACK_AUTH_OK | SLACK_AUTH_EXPIRED | SLACK_NO_TOKEN
#
# Looks for JSON with keys token + cookie at:
#   $SLACK_AUTH_FILE, or /tmp/slack-scraper/auth.json, under /tmp

set -uo pipefail

pick_auth_file() {
  local f
  for f in "${SLACK_AUTH_FILE:-}" /tmp/slack-scraper/auth.json; do
    [[ -n $f && -s $f ]] && { printf '%s\n' "$f"; return 0; }
  done
  return 1
}

auth_path=$(pick_auth_file) || {
  echo "SLACK_NO_TOKEN"
  exit 0
}

# shellcheck disable=SC2016
read -r token cookie < <(python3 - "$auth_path" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as fh:
    data = json.load(fh)
print(data.get("token", ""), data.get("cookie", ""))
PY
)

if [[ -z $token || -z $cookie ]]; then
  echo "SLACK_NO_TOKEN"
  exit 0
fi

ok=$(
  curl -sS "https://slack.com/api/auth.test" \
    -H "Authorization: Bearer ${token}" \
    -H "Cookie: d=${cookie}" \
    | python3 -c 'import json,sys; print(json.load(sys.stdin).get("ok") is True)' \
    2>/dev/null || echo False
)

if [[ $ok == True ]]; then
  echo "SLACK_AUTH_OK"
else
  echo "SLACK_AUTH_EXPIRED"
fi
