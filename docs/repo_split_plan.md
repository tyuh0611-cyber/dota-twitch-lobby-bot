# Repository split plan

Goal: split the current monorepo into two deployable repositories.

## Target repositories

### 1. dota-lobby-backend

Runs on the backend server.

Contains:

- `bot_backend/`
- backend deployment files
- backend docs
- shared project docs if needed

Must not contain:

- real Twitch tokens
- real Steam credentials
- streamer `.env`

### 2. dota-lobby-streamer-proxy

Runs on the streamer server.

Contains:

- `streamer_proxy/`
- streamer setup scripts
- streamer deployment files
- streamer README/docs

Must stay private if it contains streamer-specific deployment details.

Must not contain:

- real `.env`
- Twitch access/refresh tokens
- Steam password
- Steam shared secret

## Runtime relationship

Backend talks to streamer proxy over HTTP:

```text
backend -> streamer_proxy
```

Only shared secret between them:

```env
STREAMER_PROXY_API_KEY=...
PROXY_API_KEY=...
```

These values must match but must not be committed.

## Required streamer install inputs

Streamer should only provide this during setup:

```env
PUBLIC_BASE_URL=https://test.raze1x6.mom
PROXY_API_KEY=<generated or provided long random value>
TWITCH_CLIENT_ID=<from Twitch developer console>
TWITCH_CLIENT_SECRET=<from Twitch developer console>
DOTA_MOCK_MODE=true
```

Later, for real Dota integration:

```env
STEAM_USERNAME=
STEAM_PASSWORD=
STEAM_SHARED_SECRET=
DOTA_MOCK_MODE=false
```

The streamer should not manually provide:

```env
TWITCH_ACCESS_TOKEN=
TWITCH_REFRESH_TOKEN=
TWITCH_BROADCASTER_ID=
TWITCH_MODERATOR_ID=
```

These should be filled by OAuth/setup logic.

## Recommended split commands

Create two empty GitHub repositories first:

- `tyuh0611-cyber/dota-lobby-backend`
- `tyuh0611-cyber/dota-lobby-streamer-proxy`

Then split without preserving full monorepo history.

### Backend repo

```bash
git clone https://github.com/tyuh0611-cyber/dota-twitch-lobby-bot.git dota-lobby-backend
cd dota-lobby-backend
rm -rf streamer_proxy
mv bot_backend/* .
rmdir bot_backend
rm -f PROJECT_FILES.txt
find . -type f \
  -not -path './.git/*' \
  -not -path './.venv/*' \
  -not -path './venv/*' \
  -not -path './__pycache__/*' \
  -not -name '.env' \
  -not -name '*.pyc' \
  | sort > PROJECT_FILES.txt
git add -A
git commit -m "Split backend repository"
git remote set-url origin https://github.com/tyuh0611-cyber/dota-lobby-backend.git
git push -u origin main
```

### Streamer proxy repo

```bash
git clone https://github.com/tyuh0611-cyber/dota-twitch-lobby-bot.git dota-lobby-streamer-proxy
cd dota-lobby-streamer-proxy
rm -rf bot_backend
mv streamer_proxy/* .
rmdir streamer_proxy
rm -f PROJECT_FILES.txt
find . -type f \
  -not -path './.git/*' \
  -not -path './.venv/*' \
  -not -path './venv/*' \
  -not -path './__pycache__/*' \
  -not -name '.env' \
  -not -name '*.pyc' \
  | sort > PROJECT_FILES.txt
git add -A
git commit -m "Split streamer proxy repository"
git remote set-url origin https://github.com/tyuh0611-cyber/dota-lobby-streamer-proxy.git
git push -u origin main
```

## Server migration idea

Backend server:

```bash
cd /opt
mv dota-twitch-lobby-bot dota-twitch-lobby-bot.old
git clone https://github.com/tyuh0611-cyber/dota-lobby-backend.git dota-lobby-backend
```

Streamer server:

```bash
cd /opt
mv dota-twitch-lobby-bot dota-twitch-lobby-bot.old
git clone https://github.com/tyuh0611-cyber/dota-lobby-streamer-proxy.git dota-lobby-streamer-proxy
```

Copy only real `.env` files manually from old folders to new folders.

Never commit real `.env` files.
