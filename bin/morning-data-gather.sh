#!/usr/bin/env bash
# Collect morning-triage signals in labeled sections for agent parsers.
# Soft-fails per source so one outage does not abort the rest.
#
# Env (optional):
#   GITHUB_PR_REPOS     space-separated owner/name list for focused PR queries
#   SLACK_AUTH_FILE     path to token+cookie JSON
#   CALENDAR_CMD        command that prints today's events (any format)
#   CALENDAR_ICS_URL    if set, fetch ICS and print a short summary via curl
#
# Usage: morning-data-gather

set -uo pipefail

section() { printf '=== %s ===\n' "$1"; }

# ── GitHub ──────────────────────────────────────────────────────────
section GITHUB_USER
gh_user=$(gh api user --jq .login 2>/dev/null || echo AUTH_FAILED)
printf '%s\n' "$gh_user"

if [[ $gh_user == AUTH_FAILED ]]; then
  section GITHUB_ERROR
  echo "GitHub CLI not authenticated (try: gh auth login)"
else
  section MY_OPEN_PRS
  if [[ -n ${GITHUB_PR_REPOS:-} ]]; then
    for repo in $GITHUB_PR_REPOS; do
      gh pr list --repo "$repo" --author @me --state open \
        --json number,title,url,reviews,updatedAt \
        --jq ".[] | \"${repo}#\\(.number) | \\(.url) | \\(.title) | reviews:\\(.reviews|length) | updated:\\(.updatedAt)\"" \
        2>/dev/null || true
    done
  else
    gh search prs --author "@me" --state open --limit 30 \
      --json repository,number,title,url,updatedAt \
      --jq '.[] | "\(.repository.nameWithOwner)#\(.number) | \(.url) | \(.title) | updated:\(.updatedAt)"' \
      2>/dev/null || true
  fi

  section REVIEW_REQUESTED
  if [[ -n ${GITHUB_PR_REPOS:-} ]]; then
    for repo in $GITHUB_PR_REPOS; do
      gh pr list --repo "$repo" --review-requested @me --state open \
        --json number,title,url \
        --jq ".[] | \"${repo}#\\(.number) | \\(.url) | \\(.title)\"" \
        2>/dev/null || true
    done
  else
    gh search prs --review-requested "@me" --state open --limit 30 \
      --json repository,number,title,url \
      --jq '.[] | "\(.repository.nameWithOwner)#\(.number) | \(.url) | \(.title)"' \
      2>/dev/null || true
  fi

  section PR_COMMENTS
  mapfile -t pr_lines < <(
    gh search prs --author "@me" --state open --limit 8 \
      --json repository,number \
      --jq '.[] | "\(.repository.nameWithOwner) \(.number)"' 2>/dev/null || true
  )
  for line in "${pr_lines[@]:-}"; do
    [[ -z $line ]] && continue
    repo=${line% *}
    num=${line##* }
    echo "--- ${repo}#${num} COMMENTS ---"
    gh api "repos/${repo}/pulls/${num}/comments" --paginate \
      --jq '.[] | "\(.user.login) | \(.updated_at) | \(.body[0:120])"' 2>/dev/null || true
    echo "--- ${repo}#${num} REVIEWS ---"
    gh api "repos/${repo}/pulls/${num}/reviews" \
      --jq '.[] | "\(.user.login) | \(.state) | \(.submitted_at // "")"' 2>/dev/null || true
  done
fi

# ── Issue tracker (optional acli / Jira) ────────────────────────────
section JIRA_AUTH_CHECK
if ! command -v acli >/dev/null 2>&1; then
  echo "ACLI_NOT_INSTALLED"
elif ! acli jira workitem search --jql "assignee = currentUser() AND updated >= -1d" \
  --fields key --limit 1 &>/dev/null; then
  echo "ACLI_AUTH_EXPIRED"
else
  echo "OK"

  section JIRA_ASSIGNED
  acli jira workitem search \
    --jql "assignee = currentUser() AND status != Done ORDER BY updated DESC" \
    --fields "key,summary,status,priority" --limit 15 2>&1 || true

  section JIRA_RECENT
  acli jira workitem search \
    --jql "assignee = currentUser() AND updated >= -2d ORDER BY updated DESC" \
    --fields "key,summary,status,priority" --limit 10 2>&1 || true

  section JIRA_WATCHING
  acli jira workitem search \
    --jql "watcher = currentUser() AND assignee != currentUser() AND updated >= -2d ORDER BY updated DESC" \
    --fields "key,summary,status,priority" --limit 10 2>&1 || true

  section JIRA_COMMENTS
  keys=$(
    acli jira workitem search \
      --jql "assignee = currentUser() AND status != Done ORDER BY updated DESC" \
      --fields key --limit 12 2>&1 | grep -oE '[A-Z][A-Z0-9]+-[0-9]+' || true
  )
  for key in $keys; do
    echo "--- ${key} ---"
    acli jira workitem comment list --key "$key" 2>&1 | tail -n 20 || true
  done
fi

# ── Chat auth ───────────────────────────────────────────────────────
section SLACK_AUTH_CHECK
if command -v slack-auth-check >/dev/null 2>&1; then
  slack-auth-check
elif [[ -x $(dirname "$0")/slack-auth-check.sh ]]; then
  "$(dirname "$0")/slack-auth-check.sh"
else
  echo "SLACK_NO_TOKEN"
fi

# ── Calendar (pluggable — no OS-specific client) ────────────────────
section CALENDAR
if [[ -n ${CALENDAR_CMD:-} ]]; then
  # User-supplied command; should print human-readable events for "today"
  # shellcheck disable=SC2086
  eval "$CALENDAR_CMD" 2>/dev/null || echo "CALENDAR_CMD_FAILED"
elif [[ -n ${CALENDAR_ICS_URL:-} ]]; then
  # Minimal ICS peek: list SUMMARY/DTSTART lines (requires curl)
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL --max-time 15 "$CALENDAR_ICS_URL" 2>/dev/null \
      | grep -E '^(SUMMARY|DTSTART)' | head -n 40 \
      || echo "CALENDAR_ICS_FAILED"
  else
    echo "CALENDAR_UNAVAILABLE"
  fi
else
  echo "CALENDAR_UNAVAILABLE"
  echo "(set CALENDAR_CMD or CALENDAR_ICS_URL to enable)"
fi

section DONE
