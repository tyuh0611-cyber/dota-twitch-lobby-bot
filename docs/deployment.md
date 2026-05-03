# Deployment

## Local test database

From repository root:

```bash
docker compose up -d postgres
```

Default local database URL:

```text
postgresql+asyncpg://dota_lobby:change_me_for_local_tests@127.0.0.1:5432/dota_lobby
```

## Streamer proxy

```bash
cd streamer_proxy
cp .env.example .env
nano .env
bash install.sh
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8081
```

## Bot backend

```bash
cd bot_backend
cp .env.example .env
nano .env
bash install.sh
source .venv/bin/activate
python -m app.main
```

## Production notes

Use systemd services later. For MVP testing, manual terminal launch is enough.
