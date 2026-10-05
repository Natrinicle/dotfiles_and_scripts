#!/usr/bin/env bash
# Copy user units for the RPerks coupon activator, then enable the timer.
# App files must already live at $HOME/.local/bin/rperks-activate-coupons
# (install.sh --bin, or copy bin/rperks-activate-coupons/ yourself).
set -euo pipefail

UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$UNIT_DIR"

install -m 0644 "$SRC_DIR/rperks-activate-install.service" "$UNIT_DIR/"
install -m 0644 "$SRC_DIR/rperks-activate.service" "$UNIT_DIR/"
install -m 0644 "$SRC_DIR/rperks-activate.timer" "$UNIT_DIR/"

systemctl --user daemon-reload
systemctl --user enable --now rperks-activate.timer
systemctl --user enable rperks-activate-install.service

echo "Timer:"
systemctl --user list-timers rperks-activate.timer --no-pager
echo
echo "Manual run:  systemctl --user start rperks-activate.service"
echo "Logs:        journalctl --user -u rperks-activate.service -u rperks-activate-install.service -e"
