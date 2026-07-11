#!/usr/bin/env bash
# Append text to Speakr recording notes without clobbering existing content.
# The Speakr notes PUT replaces the whole field — we read, merge, then write.
#
# Usage:
#   speakr-notes-append <recording-id> <text...>
#   speakr-notes-append <recording-id> -   # read body from stdin

set -uo pipefail

resolve_memory_root() {
  if [[ -n ${MEMORY_ROOT:-} ]]; then
    printf '%s\n' "$MEMORY_ROOT"
    return
  fi
  local cand
  for cand in "${HOME}/.claude/memory" "${HOME}/.grok/memory"; do
    [[ -f ${cand}/speakr-api-token.txt ]] && {
      printf '%s\n' "$cand"
      return
    }
  done
  printf '%s\n' "${HOME}/.claude/memory"
}

MEMORY_ROOT=$(resolve_memory_root)
TOKEN_FILE=${SPEAKR_TOKEN_FILE:-${MEMORY_ROOT}/speakr-api-token.txt}
API_BASE=${SPEAKR_API_BASE:-http://localhost:8899/api/v1}

rid=${1:?usage: speakr-notes-append <recording-id> <text|->}
shift

if [[ ${1:-} == - ]]; then
  addition=$(cat)
else
  addition=$*
fi

if [[ ! -r $TOKEN_FILE ]]; then
  echo "speakr-notes-append: missing token ${TOKEN_FILE}" >&2
  exit 1
fi

token=$(tr -d '[:space:]' <"$TOKEN_FILE")

python3 - "$token" "$API_BASE" "$rid" "$addition" <<'PY'
import json
import sys
import urllib.error
import urllib.request

token, base, rid, addition = sys.argv[1:5]
headers = {"Authorization": f"Bearer {token}"}

def req(method, url, data=None):
    body = None if data is None else json.dumps(data).encode()
    h = dict(headers)
    if body is not None:
        h["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=body, headers=h, method=method)
    with urllib.request.urlopen(r) as resp:
        return json.loads(resp.read().decode())

url = f"{base.rstrip('/')}/recordings/{rid}/notes"
try:
    current = req("GET", url).get("notes") or ""
except urllib.error.HTTPError as exc:
    sys.stderr.write(f"read failed: {exc}\n")
    sys.exit(1)

merged = f"{current.rstrip()}\n\n{addition}" if current.strip() else addition
try:
    out = req("PUT", url, {"notes": merged})
except urllib.error.HTTPError as exc:
    sys.stderr.write(f"write failed: {exc}\n")
    sys.exit(1)

print("OK" if out.get("success", True) else json.dumps(out))
PY
