# Dota Twitch Lobby Bot

MVP project for managing Dota 2 custom-lobby invites with Twitch chatters and Telegram controls.

## Components

- `streamer_proxy` — runs on streamer server, stores Twitch/Steam credentials, exposes limited API.
- `bot_backend` — runs on bot/backend server, stores PostgreSQL data, Telegram commands, selection logic.
- `docs` — deployment, security and architecture notes.

## Safety

Never commit real `.env` files, Twitch tokens, Steam credentials, Telegram tokens or database passwords.
Use `.env.example` only.

## Current status

This is a test/MVP scaffold. Dota Game Coordinator integration is represented by an adapter interface and mock implementation first, so the API/DB/Telegram flow can be tested safely before real Steam/Dota integration is connected.
