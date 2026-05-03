#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/tyuh0611-cyber/dota-twitch-lobby-bot.git}"
APP_DIR="${APP_DIR:-/opt/dota-twitch-lobby-bot}"
SERVICE_USER="dota-streamer-proxy"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root. Example: sudo bash scripts/install_streamer_proxy.sh"
  exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This installer currently supports Debian/Ubuntu servers with apt-get."
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl git nano python3 python3-venv python3-pip systemd

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --home "$APP_DIR/streamer_proxy" --shell /usr/sbin/nologin "$SERVICE_USER"
fi

mkdir -p "$APP_DIR"
if [ ! -d "$APP_DIR/.git" ]; then
  rm -rf "$APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" pull
fi

cd "$APP_DIR/streamer_proxy"
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  chmod 600 .env
  echo "Created $APP_DIR/streamer_proxy/.env"
  echo "Fill it before starting service."
fi

chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR/streamer_proxy"
cp "$APP_DIR/streamer_proxy/systemd/streamer-proxy.service" /etc/systemd/system/streamer-proxy.service
systemctl daemon-reload
systemctl enable streamer-proxy

echo ""
echo "Installed streamer proxy."
echo "Next steps:"
echo "1) nano $APP_DIR/streamer_proxy/.env"
echo "2) systemctl restart streamer-proxy"
echo "3) systemctl status streamer-proxy"
