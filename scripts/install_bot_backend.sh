#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/tyuh0611-cyber/dota-twitch-lobby-bot.git}"
APP_DIR="${APP_DIR:-/opt/dota-twitch-lobby-bot}"
SERVICE_USER="dota-lobby-bot"
INSTALL_DOCKER="${INSTALL_DOCKER:-true}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root. Example: sudo bash scripts/install_bot_backend.sh"
  exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This installer currently supports Debian/Ubuntu servers with apt-get."
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl git nano python3 python3-venv python3-pip postgresql-client systemd

if [ "$INSTALL_DOCKER" = "true" ] && ! command -v docker >/dev/null 2>&1; then
  apt-get install -y docker.io docker-compose-plugin
  systemctl enable --now docker
fi

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --home "$APP_DIR/bot_backend" --shell /usr/sbin/nologin "$SERVICE_USER"
fi

mkdir -p "$APP_DIR"
if [ ! -d "$APP_DIR/.git" ]; then
  rm -rf "$APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" pull
fi

if [ "$INSTALL_DOCKER" = "true" ]; then
  cd "$APP_DIR"
  docker compose up -d postgres
fi

cd "$APP_DIR/bot_backend"
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  chmod 600 .env
  echo "Created $APP_DIR/bot_backend/.env"
  echo "Fill it before starting service."
fi

chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR/bot_backend"
cp "$APP_DIR/bot_backend/systemd/dota-lobby-bot.service" /etc/systemd/system/dota-lobby-bot.service
systemctl daemon-reload
systemctl enable dota-lobby-bot

echo ""
echo "Installed bot backend."
echo "Next steps:"
echo "1) nano $APP_DIR/bot_backend/.env"
echo "2) systemctl restart dota-lobby-bot"
echo "3) systemctl status dota-lobby-bot"
