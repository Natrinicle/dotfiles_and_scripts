#!/usr/bin/env bash
# Thin HTTP client for a local Speakr (or compatible) REST API.
#
# Usage:
#   speakr-api [get|post|put|patch|delete] <path-under-/api/v1> [json-body]
# Defaults: get stats
#
# Token file: $SPEAKR_TOKEN_FILE or {MEMORY_ROOT}/speakr-api-token.txt
# Base URL:   $SPEAKR_API_BASE (default http://localhost:8899/api/v1)

set -uo pipefail

resolve_memory_root() {
  if [[ -n ${MEMORY_ROOT:-} ]]; then
    printf '%s\n' "$MEMORY_ROOT"
    return
  fi
  local cand
  for cand in "${HOME}/.claude/memory" "${HOME}/.grok/memory"; do
    if [[ -f ${cand}/speakr-api-token.txt ]]; then
      printf '%s\n' "$cand"
      return
    fi
  done
  printf '%s\n' "${HOME}/.claude/memory"
}

MEMORY_ROOT=$(resolve_memory_root)
TOKEN_FILE=${SPEAKR_TOKEN_FILE:-${MEMORY_ROOT}/speakr-api-token.txt}
API_BASE=${SPEAKR_API_BASE:-http://localhost:8899/api/v1}

if [[ ! -r $TOKEN_FILE ]]; then
  echo "speakr-api: missing token file: ${TOKEN_FILE}" >&2
  exit 1
fi

token=$(tr -d '[:space:]' <"$TOKEN_FILE")
method=$(printf '%s' "${1:-get}" | tr '[:lower:]' '[:upper:]')
path=${2:-stats}
payload=${3:-{}}

auth=(-H "Authorization: Bearer ${token}")

case $method in
  GET)
    curl -sS "${auth[@]}" "${API_BASE}/${path}"
    ;;
  POST | PUT | PATCH)
    curl -sS -X "$method" "${auth[@]}" \
      -H "Content-Type: application/json" \
      -d "$payload" \
      "${API_BASE}/${path}"
    ;;
  DELETE)
    curl -sS -X DELETE "${auth[@]}" "${API_BASE}/${path}"
    ;;
  *)
    echo "usage: speakr-api <get|post|put|patch|delete> <endpoint> [json-body]" >&2
    exit 2
    ;;
esac
