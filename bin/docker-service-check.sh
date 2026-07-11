#!/usr/bin/env bash
# Report whether a Docker container name is running.
# Prints one of: RUNNING | STOPPED | NOT_FOUND
#
# Usage: docker-service-check <name-substring>

set -uo pipefail

name=${1:?usage: docker-service-check <container-name>}

if ! command -v docker >/dev/null 2>&1; then
  echo "NOT_FOUND"
  exit 0
fi

live=$(docker ps --filter "name=${name}" --format '{{.Names}}' 2>/dev/null | head -1)
if [[ -n $live ]]; then
  echo "RUNNING"
  exit 0
fi

any=$(docker ps -a --filter "name=${name}" --format '{{.Names}}' 2>/dev/null | head -1)
if [[ -n $any ]]; then
  echo "STOPPED"
else
  echo "NOT_FOUND"
fi
