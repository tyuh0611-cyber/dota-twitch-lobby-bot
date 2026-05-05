from datetime import timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Player
from .settings_service import get_all_settings, setting_bool, split_names

STRATEGY_LABELS = {
    'oldest_played': 'First who played longest ago',
    'most_slots': 'First with most slots',
    'recent_slot': 'First who recently got a slot',
    'recent_played': 'First who played recently',
    'most_active': 'First most active',
}


def _timestamp(value) -> float:
    if not value:
        return 0.0
    return value.replace(tzinfo=timezone.utc).timestamp()


def _reason(player: Player, strategy: str, is_special: bool, is_online: bool) -> str:
    parts = []
    if is_special:
        parts.append('special-first')
    if is_online:
        parts.append('online in Twitch chat')
    parts.append(STRATEGY_LABELS.get(strategy, STRATEGY_LABELS['oldest_played']))
    return ' · '.join(parts)


async def ranked_queue_players(session: AsyncSession, online_twitch_names: set[str] | None = None) -> tuple[list[dict], dict[str, str]]:
    online_twitch_names = {x.lower() for x in (online_twitch_names or set())}
    queue_settings = await get_all_settings(session)

    result = await session.execute(
        select(Player).where(
            Player.is_blacklisted.is_(False),
            Player.slots_left > 0,
        )
    )
    players = list(result.scalars().all())

    require_online = setting_bool(queue_settings.get('require_twitch_online', 'false'))
    if require_online:
        players = [p for p in players if p.twitch_name and p.twitch_name.lower() in online_twitch_names]

    special_names = split_names(queue_settings.get('special_first_twitch_names', ''))
    strategy = queue_settings.get('queue_strategy', 'oldest_played')

    def special_rank(player: Player) -> int:
        return 0 if player.twitch_name and player.twitch_name.lower() in special_names else 1

    def sort_key(player: Player) -> tuple:
        if strategy == 'most_slots':
            return (special_rank(player), -player.slots_left, _timestamp(player.last_played_at))
        if strategy == 'recent_slot':
            return (special_rank(player), -_timestamp(player.last_slot_added_at), _timestamp(player.last_played_at))
        if strategy == 'recent_played':
            return (special_rank(player), -_timestamp(player.last_played_at), -player.slots_left)
        if strategy == 'most_active':
            return (special_rank(player), -(player.games_played or 0), -player.slots_left)
        return (special_rank(player), _timestamp(player.last_played_at), -player.slots_left)

    ranked = []
    for index, player in enumerate(sorted(players, key=sort_key), start=1):
        twitch_key = player.twitch_name.lower() if player.twitch_name else ''
        is_special = twitch_key in special_names
        is_online = twitch_key in online_twitch_names if twitch_key else False
        ranked.append({
            'rank': index,
            'player': player,
            'is_special': is_special,
            'is_online': is_online,
            'reason': _reason(player, strategy, is_special, is_online),
        })
    return ranked, queue_settings


async def select_next_player(session: AsyncSession, online_twitch_names: set[str] | None = None) -> Player | None:
    ranked, _ = await ranked_queue_players(session, online_twitch_names)
    if not ranked:
        return None
    return ranked[0]['player']
