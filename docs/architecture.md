# Architecture

## Servers

```text
Streamer server
- streamer_proxy FastAPI app
- Twitch OAuth credentials
- Steam/Dota credentials later
- limited API endpoints for chatters, lobby state and invites

Backend server
- bot_backend Telegram bot
- PostgreSQL database
- player slots, history, queue and selection logic
```

## Request flow

```text
Telegram admin command
  -> bot_backend
  -> PostgreSQL
  -> streamer_proxy API
  -> Twitch API / Dota adapter
```

## Trust model

The streamer server never sends Twitch or Steam tokens to the backend server. The backend receives only normalized data such as chatters, lobby members and invite results.
