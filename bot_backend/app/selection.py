from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Player
from .settings_service import get_all_settings, setting_bool, split_names


async def select_next_player(session: AsyncSession, online_twitch_names: set[str] | None = None) -> Player | None:
    online_twitch_names = {x.lower() for x in (online_twitch_names or set())}
    queue_settings = await get_all_settings(session)

    result = await session.execute(
        select(Player).where(
            Player.is_blacklisted.is_(False),
            Player.slots_left > 0,
        )
    )
    players = list(result.scalars().all())

    if setting_bool(queue_settings.get('require_twitch_online', 'false')):
        players = [p for p in players if p.twitch_name and p.twitch_name.lower() in online_twitch_names]

    if not players:
        return None

    special_names = split_names(queue_settings.get('special_first_twitch_names', ''))
    strategy = queue_settings.get('queue_strategy', 'oldest_played')

    def last_played_timestamp(player: Player) -> float:
        if not player.last_played_at:
            return 0.0
        return player.last_played_at.replace(tzinfo=timezone.utc).timestamp()

    def last_slot_timestamp(player: Player) -> float:
        if not player.last_slot_added_at:
            return 0.0
        return player.last_slot_added_at.replace(tzinfo=timezone.utc).timestamp()

    def special_rank(player: Player) -> int:
        return 0 if player.twitch_name and player.twitch_name.lower() in special_names else 1

    def sort_key(player: Player) -> tuple:
        if strategy == 'most_slots':
            return (special_rank(player), -player.slots_left, last_played_timestamp(player))
        if strategy == 'recent_slot':
            return (special_rank(player), -last_slot_timestamp(player), last_played_timestamp(player))
        if strategy == 'recent_played':
            return (special_rank(player), -last_played_timestamp(player), -player.slots_left)
        if strategy == 'most_active':
            return (special_rank(player), -(player.games_played or 0), -player.slots_left)
        return (special_rank(player), last_played_timestamp(player), -player.slots_left)

    return sorted(players, key=sort_key)[0]
