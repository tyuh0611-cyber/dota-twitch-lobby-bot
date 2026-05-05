# Project context

This file preserves the important working context from the ChatGPT setup session.

## Repository

- Repository: `tyuh0611-cyber/dota-twitch-lobby-bot`
- Main domain for web dashboard: `foryou.raze1x6.mom`
- Backend server hosts the web dashboard, Telegram bot backend and PostgreSQL.
- Streamer server hosts the streamer proxy with Twitch/Steam/Dota secrets.

## Architecture

The system is split into two servers:

1. Backend server:
   - PostgreSQL database
   - Telegram bot backend, currently still present as fallback
   - FastAPI web dashboard
   - Nginx reverse proxy
   - Certbot/HTTPS for `foryou.raze1x6.mom`

2. Streamer server:
   - `streamer_proxy`
   - Keeps Twitch/Steam/Dota tokens and credentials on the streamer side
   - Exposes only limited authenticated HTTP endpoints to backend
   - Later replaces mock Dota adapter with real Dota GC adapter

Backend should not store or see streamer tokens.

## Current web dashboard direction

The preferred interface is now the web dashboard, not Telegram commands.
Telegram remains useful as a fallback/admin channel, but main work should happen in the web UI.

The dashboard has been evolving into a single Control Center page:

- Settings block
- Lobby block
- Add player / slots block
- Priority queue table
- Inline editing
- Action buttons
- Notifications/toasts

The old separate pages can remain as backup, but the main page `/` should contain everything important.

## Current desired dashboard layout

The user asked to remove from the main page:

- `Total players`
- `Active players`
- `Slots left`
- `Blacklisted`
- separate `Queue logic` block showing current strategy/settings

Main page should keep:

- Settings block only for settings
- Lobby block
- Add player / slots
- Priority queue table

Settings and Lobby blocks should be vertical, larger and clearer, not small horizontal widgets.

The page should be compact enough so queue/request actions are visible without too much scrolling.

## Queue table requirements

Queue should be a ranked table, not a single candidate card.

Each row should show:

- Rank / priority
- Why this player is prioritized
- Twitch name
- Dota name / Dota ID
- Steam ID
- Slots left
- Games played
- Comment
- Actions

Actions per row:

- Save inline edits
- Invite player to lobby
- Charge `-1 slot`
- Block / blacklist

Inline editing requirement:

- Double-click table information to edit it in place
- After editing, press `Save` / `Save row`
- Editable fields include Twitch, Dota name, Steam ID, slots, comment

Quick invite:

- Quick invite should invite the first N players by current Settings strategy
- Needs a compact number control without browser default spinner arrows

## Settings logic

Settings are database-backed via `bot_settings`, not only `.env`.

Known settings:

- `require_twitch_online`
- `special_first_twitch_names`
- `queue_strategy`
- `invite_timeout_seconds`

Queue strategies:

- `oldest_played` — first who played longest ago
- `most_slots` — first with most slots
- `recent_slot` — first who recently got a slot
- `recent_played` — first who played recently
- `most_active` — first most active

Special Twitch names, such as `EZ25`, should be ranked before normal users when eligible.

## Styling preferences

User wants:

- Dota-like dark theme
- Pleasant, clean, compact UI
- Better alignment and less empty space
- Clearer action visibility
- Avoid oversized blocks
- Custom number steppers with `+` and `−`
- Remove default white browser number spinner arrows
- Notifications after actions

Previously fixed:

- Static CSS serving via FastAPI `StaticFiles`
- Logo sizing issue
- SVG logo cross overlay removed

## Backend deployment commands

Typical update flow on backend server:

```bash
cd /opt/dota-twitch-lobby-bot
git pull
systemctl restart dota-lobby-web
```

For harder cache issues:

```bash
systemctl restart dota-lobby-web
```

Then in browser:

```text
CTRL + F5
https://foryou.raze1x6.mom/?v=1000
```

Check CSS deployed:

```bash
grep -n "webkit-inner-spin-button" /opt/dota-twitch-lobby-bot/bot_backend/app/static/style.css
```

## Streamer proxy endpoints

Backend calls streamer proxy using `X-Api-Key`.

Endpoints:

```text
GET  /health
GET  /chatters
GET  /dota/status
GET  /dota/lobby
POST /dota/invite
GET  /twitch/auth-url
GET  /twitch/callback
```

Important: `PROXY_API_KEY` on streamer server must match `STREAMER_PROXY_API_KEY` on backend server.
Do not expose real keys in chat or docs.

## Dota API / GC notes

There is no simple public HTTP Dota endpoint for custom lobby invites.
The real Dota part must be implemented through Steam Client + Dota 2 Game Coordinator, usually via Python/Node libraries and protobuf messages.

The backend should continue to talk only to streamer_proxy over HTTP. The streamer proxy internally handles Steam/Dota GC.

Real Dota flow:

```text
backend web action -> streamer_proxy /dota/invite -> Steam login -> Dota GC -> invite_to_lobby
```

## Current project stages

Already done / mostly done:

- Backend install flow
- PostgreSQL running
- Telegram backend running
- Streamer proxy mock mode
- Mock lobby and mock invite
- Domain and nginx config
- Certbot setup path
- Web dashboard MVP
- Static assets
- Control Center direction
- Settings stored in DB
- Ranked queue table
- Inline editing JS
- Toast notification foundation

Next likely tasks:

1. Ensure latest layout/CSS is deployed and visually correct.
2. Continue polishing Control Center compact layout.
3. Improve toasts and action feedback if needed.
4. Add CSRF protection for forms.
5. Add HTTPS/security hardening if not already fully done.
6. Add Twitch OAuth/config completion.
7. Replace mock Dota adapter with real Dota GC adapter.
8. Add match history / mini-Dotabuff features.

## Security notes

- Avoid raw SQL string concatenation.
- Continue using SQLAlchemy ORM / parameterized queries.
- Keep secrets in `.env` only.
- Streamer tokens must stay on streamer server.
- Backend should only receive limited data from streamer proxy.
- Use strong `WEB_SESSION_SECRET`, `WEB_ADMIN_PASSWORD`, and proxy API key.
- Rotate exposed proxy keys after tests.

## User preferences

- User prefers concise, direct instructions.
- User often asks for exact commands.
- User wants practical step-by-step setup and visible results quickly.
- User prefers not to overcomplicate deployment for the streamer; streamer-side setup should be as close to one command as possible.
