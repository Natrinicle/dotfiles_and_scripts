#!/usr/bin/env bash
# Copy MemPalace hub + daemon user units. Does not enable or start them.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
DROP_IN="${UNIT_DIR}/mempalace-mcp-http.service.d"

mkdir -p "$DROP_IN"
install -m 644 "$ROOT/systemd/mempalace-mcp-http.service" "$UNIT_DIR/"
install -m 644 "$ROOT/systemd/mempalace-daemon.service" "$UNIT_DIR/"

shopt -s nullglob
for conf in "$ROOT/systemd/mempalace-mcp-http.service.d/"*.conf; do
	install -m 644 "$conf" "$DROP_IN/"
done

systemctl --user daemon-reload

cat <<EOF
Copied user units to ${UNIT_DIR}

Create palace dirs, start Qdrant, then:
  systemctl --user enable --now mempalace-mcp-http.service mempalace-daemon.service

Optional GPU: copy cuda-cudnn.conf.example to ${DROP_IN}/cuda-cudnn.conf
and set LD_LIBRARY_PATH, then daemon-reload.
EOF
