#!/usr/bin/env bash
# Show Speakr recording job status from the local SQLite DB (+ queue stats).
#
# Usage: speakr-poll [recording-id ...]
# Env:   SPEAKR_DB  (default: $HOME/docker/speakr/instance/transcriptions.db)

set -uo pipefail

db=${SPEAKR_DB:-${HOME}/docker/speakr/instance/transcriptions.db}
ids=("$@")
if ((${#ids[@]} == 0)); then
  # If none given, list recent non-complete jobs + a few latest ids
  if command -v sqlite3 >/dev/null 2>&1 && [[ -f $db ]]; then
    mapfile -t ids < <(sqlite3 "$db" \
      "SELECT id FROM recording ORDER BY id DESC LIMIT 8;")
  fi
fi

if ((${#ids[@]} == 0)); then
  echo "speakr-poll: no recording ids" >&2
  exit 1
fi

echo "Speakr status @ $(date '+%H:%M:%S')"
echo "----------------------------------------"

all_complete=1
for id in "${ids[@]}"; do
  status=$(sqlite3 "$db" "SELECT status FROM recording WHERE id=${id};" 2>/dev/null || echo "?")
  title=$(sqlite3 "$db" "SELECT substr(coalesce(title,''),1,48) FROM recording WHERE id=${id};" 2>/dev/null || echo "")
  chars=$(sqlite3 "$db" "SELECT coalesce(length(transcription),0) FROM recording WHERE id=${id};" 2>/dev/null || echo 0)
  mark="·"
  case $status in
    COMPLETED) mark="+" ;;
    FAILED) mark="x"; all_complete=0 ;;
    *) all_complete=0; mark="~" ;;
  esac
  printf '  [%s] #%s  %-12s  %s chars  %s\n' "$mark" "$id" "$status" "$chars" "$title"
done

echo
if command -v speakr-api >/dev/null 2>&1; then
  speakr-api get stats 2>/dev/null | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    q = d.get("queue") or {}
    print("queue: %s processing, %s queued" % (
        q.get("jobs_processing", "?"),
        q.get("jobs_queued", "?"),
    ))
except Exception:
    pass
' 2>/dev/null || true
elif command -v speakr-api.sh >/dev/null 2>&1; then
  speakr-api.sh get stats 2>/dev/null | head -c 200 || true
fi

if [[ $all_complete -eq 1 ]]; then
  echo
  echo "ALL_DONE"
fi
