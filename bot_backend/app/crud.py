from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Match, MatchPlayer, Player, PlayerSlotLog


async def get_player_by_dota_id(session: AsyncSession, dota_id: str) -> Player | None:
    result = await session.execute(select(Player).where(Player.dota_id == dota_id))
    return result.scalar_one_or_none()


async def get_player_by_steam_id(session: AsyncSession, steam_id: str) -> Player | None:
    result = await session.execute(select(Player).where(Player.steam_id == steam_id))
    return result.scalar_one_or_none()


async def add_slots(session: AsyncSession, dota_id: str, slots: int, created_by: str | None = None) -> Player:
    player = await get_player_by_dota_id(session, dota_id)
    now = datetime.utcnow()
    if player is None:
        player = Player(dota_id=dota_id, slots_total=0, slots_left=0, last_slot_added_at=now)
        session.add(player)
        await session.flush()

    old_slots = player.slots_left
    player.slots_left += slots
    player.slots_total += max(slots, 0)
    player.last_slot_added_at = now

    session.add(PlayerSlotLog(
        player_id=player.id,
        change_amount=slots,
        old_slots_left=old_slots,
        new_slots_left=player.slots_left,
        reason='manual_add_slots',
        created_by=created_by,
    ))
    await session.commit()
    await session.refresh(player)
    return player


async def set_slots(session: AsyncSession, dota_id: str, slots: int, created_by: str | None = None) -> Player:
    player = await get_player_by_dota_id(session, dota_id)
    if player is None:
        player = Player(dota_id=dota_id, slots_total=max(slots, 0), slots_left=slots)
        session.add(player)
        await session.flush()

    old_slots = player.slots_left
    player.slots_left = slots
    player.slots_total = max(player.slots_total, slots)
    session.add(PlayerSlotLog(
        player_id=player.id,
        change_amount=slots - old_slots,
        old_slots_left=old_slots,
        new_slots_left=slots,
        reason='manual_set_slots',
        created_by=created_by,
    ))
    await session.commit()
    await session.refresh(player)
    return player


async def charge_slot_after_game(
    session: AsyncSession,
    dota_id: str,
    created_by: str | None = None,
    match_id: str | None = None,
    lobby_id: str | None = None,
) -> Player | None:
    player = await get_player_by_dota_id(session, dota_id)
    if not player:
        return None

    old_slots = player.slots_left
    if player.slots_left > 0:
        player.slots_left -= 1
    player.games_played += 1
    player.last_played_at = datetime.utcnow()

    session.add(PlayerSlotLog(
        player_id=player.id,
        change_amount=-1 if old_slots > 0 else 0,
        old_slots_left=old_slots,
        new_slots_left=player.slots_left,
        reason='after_game_charge',
        created_by=created_by,
    ))

    match = Match(match_id=match_id, lobby_id=lobby_id, ended_at=datetime.utcnow())
    session.add(match)
    await session.flush()
    session.add(MatchPlayer(
        match_id=match.id,
        player_id=player.id,
        dota_id=player.dota_id,
        steam_id=player.steam_id,
        dota_name=player.dota_name,
        twitch_name=player.twitch_name,
        slots_before=old_slots,
        slots_after=player.slots_left,
        slot_was_charged=old_slots > 0,
    ))
    await session.commit()
    await session.refresh(player)
    return player


async def link_player(
    session: AsyncSession,
    dota_id: str,
    twitch_name: str | None,
    steam_id: str | None,
    dota_name: str | None,
) -> Player:
    player = await get_player_by_dota_id(session, dota_id)
    if player is None:
        player = Player(dota_id=dota_id, slots_total=0, slots_left=0)
        session.add(player)
        await session.flush()

    player.twitch_name = twitch_name
    player.steam_id = steam_id
    player.dota_name = dota_name
    await session.commit()
    await session.refresh(player)
    return player


async def set_comment(session: AsyncSession, dota_id: str, comment: str | None) -> Player | None:
    player = await get_player_by_dota_id(session, dota_id)
    if not player:
        return None
    player.comment = comment
    await session.commit()
    await session.refresh(player)
    return player


async def blacklist_player(session: AsyncSession, dota_id: str, reason: str | None = None) -> Player | None:
    player = await get_player_by_dota_id(session, dota_id)
    if not player:
        return None
    player.is_blacklisted = True
    player.blacklist_reason = reason
    await session.commit()
    await session.refresh(player)
    return player


async def unblacklist_player(session: AsyncSession, dota_id: str) -> Player | None:
    player = await get_player_by_dota_id(session, dota_id)
    if not player:
        return None
    player.is_blacklisted = False
    player.blacklist_reason = None
    await session.commit()
    await session.refresh(player)
    return player


async def recent_slot_logs(session: AsyncSession, dota_id: str, limit: int = 10) -> list[PlayerSlotLog]:
    player = await get_player_by_dota_id(session, dota_id)
    if not player:
        return []
    result = await session.execute(
        select(PlayerSlotLog)
        .where(PlayerSlotLog.player_id == player.id)
        .order_by(PlayerSlotLog.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
