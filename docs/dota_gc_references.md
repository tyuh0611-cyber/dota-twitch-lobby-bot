# Dota 2 Game Coordinator references

There is no public HTTP REST API for Dota 2 custom lobby members or lobby invites.
Lobby/invite automation is done through Steam network + Dota 2 Game Coordinator messages.

## Main references

- ValvePython dota2 docs: https://dota2.readthedocs.io/en/stable/
- ValvePython dota2 GitHub: https://github.com/ValvePython/dota2
- ValvePython steam GitHub: https://github.com/ValvePython/steam
- node-dota2 GitHub: https://github.com/Arcana/node-dota2
- SteamKit2 GitHub: https://github.com/SteamRE/SteamKit
- SteamKit protobufs: https://github.com/SteamRE/SteamKit/tree/master/Resources/Protobufs
- Dota 2 protobufs mirror/reference: https://github.com/SteamDatabase/GameTracking-Dota2/tree/master/Protobufs

## Concepts to search in docs/code

- Game Coordinator
- app id 570
- practice lobby
- lobby_changed
- invite_to_lobby
- create_practice_lobby
- join_practice_lobby
- leave_practice_lobby
- CMsgPracticeLobbySetDetails
- CMsgPracticeLobbyJoin
- CMsgPracticeLobbyKick
- CMsgInviteToLobby

## Project API boundary

Backend calls only streamer_proxy:

```text
GET  /dota/status
GET  /dota/lobby
POST /dota/invite
```

streamer_proxy then talks to Steam/Dota GC internally.
