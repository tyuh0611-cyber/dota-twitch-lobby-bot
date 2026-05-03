#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/tyuh0611-cyber/dota-twitch-lobby-bot.git}"
APP_DIR="${APP_DIR:-/opt/dota-twitch-lobby-bot}"
SERVICE_USER="dota-lobby-bot"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root with sudo."
  exit 1
fi

apt-get update
apt-get install -y git python3 python3-venv python3-pip postgresql-client

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --home "$APP_DIR/bot_backend" --shell /usr/sbin/nologin "$SERVICE_USER"
fi

if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" pull
fi

cd "$APP_DIR/bot_backend"
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  chmod 600 .env
  echo "Created backend env file. Fill it before start."
fi

chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR/bot_backend"
cp "$APP_DIR/bot_backend/systemd/dota-lobby-bot.service" /etc/systemd/system/dota-lobby-bot.service
systemctl daemon-reload
systemctl enable dota-lobby-bot

echo "Installed bot backend."
echo "Edit env: $APP_DIR/bot_backend/.env"
echo "Start: systemctl restart dota-lobby-bot"
echo "Status: systemctl status dota-lobby-bot"
