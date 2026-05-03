#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "streamer_proxy installed. Copy .env.example to .env and run:"
echo "source .venv/bin/activate"
echo "uvicorn app.main:app --host 0.0.0.0 --port 8081"
