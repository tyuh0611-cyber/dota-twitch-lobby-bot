#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "bot_backend installed. Copy .env.example to .env and run:"
echo "source .venv/bin/activate"
echo "python -m app.main"
