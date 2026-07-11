#!/usr/bin/env bash
# Install the daily claude-activity systemd user timer + its dedicated clone.
# Idempotent: safe to re-run; re-running rewrites the unit files in place.
# Run this only AFTER the feature is merged to main — the service executes the
# script from the dedicated clone, which tracks main.
set -euo pipefail

REPO_URL="${CA_REPO_URL:-git@github-personal:castorrr/castorrr.github.io.git}"
REPO_DIR="${CA_REPO_DIR:-$HOME/.local/share/claude-activity/repo}"
UNIT_DIR="${CA_UNIT_DIR:-$HOME/.config/systemd/user}"

if [ ! -d "$REPO_DIR/.git" ]; then
  mkdir -p "$(dirname "$REPO_DIR")"
  git clone --branch main "$REPO_URL" "$REPO_DIR"
  echo "cloned $REPO_URL -> $REPO_DIR"
else
  echo "dedicated clone already present: $REPO_DIR"
fi

mkdir -p "$UNIT_DIR"

cat > "$UNIT_DIR/claude-activity.service" <<EOF
[Unit]
Description=Update the Claude Code activity ledger on the portfolio site

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 $REPO_DIR/scripts/update-claude-activity.py
EOF

cat > "$UNIT_DIR/claude-activity.timer" <<EOF
[Unit]
Description=Daily update of the Claude activity ledger

[Timer]
OnCalendar=*-*-* 21:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

echo "wrote $UNIT_DIR/claude-activity.{service,timer}"

if [ "${CA_SKIP_SYSTEMD:-0}" != "1" ]; then
  systemctl --user daemon-reload
  systemctl --user enable --now claude-activity.timer
  systemctl --user list-timers claude-activity.timer --no-pager
fi
