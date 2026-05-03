# Security

## Rules

- Never commit real `.env` files.
- Never log tokens, API keys, passwords or Authorization headers.
- Keep Twitch and Steam credentials only on the streamer server.
- Backend server must call only limited streamer_proxy endpoints.
- Do not build a universal Twitch proxy endpoint.
- Allow only known Telegram admin IDs.
- Use SQLAlchemy queries and prepared parameters, not string-formatted SQL.
- Use HTTPS between servers for production.
- Use IP allow-listing on streamer_proxy when possible.

## Secrets

Use `.env` files with restrictive permissions:

```bash
chmod 600 .env
```

For production, prefer systemd EnvironmentFile, Docker secrets, Vault or cloud secret managers.
