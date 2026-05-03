from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .config import settings
from .models import Player


async def select_next_player(session: AsyncSession, online_twitch_names: set[str] | None = None) -> Player | None:
    online_twitch_names = {x.lower() for x in (online_twitch_names or set())}

    result = await session.execute(
        select(Player).where(
            Player.is_blacklisted.is_(False),
            Player.slots_left > 0,
        )
    )
    players = list(result.scalars().all())

    if settings.require_twitch_online:
        players = [p for p in players if p.twitch_name and p.twitch_name.lower() in online_twitch_names]

    if not players:
        return None

    def sort_key(player: Player) -> tuple:
        special_rank = 0 if player.twitch_name and player.twitch_name.lower() in settings.special_names else 1
        last_played = player.last_played_at.isoformat() if player.last_played_at else ''
        return (
            special_rank,
            last_played,
            -player.slots_left,
            -(player.games_played or 0),
        )

    return sorted(players, key=sort_key)[0]
