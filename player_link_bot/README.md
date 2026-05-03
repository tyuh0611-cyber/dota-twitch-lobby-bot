# Player Link Bot Template

Optional future bot for self-service linking by players.

Planned flow:

```text
/player starts bot
-> sends Twitch login
-> sends Dota ID / SteamID64
-> bot stores pending link request
-> streamer/admin approves in main bot
```

For MVP, links are created manually by streamer/admin using:

```text
/link DOTA_ID TWITCH_NAME STEAM_ID [DOTA_NAME]
```
