from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Player, PlayerSlotLog


async def get_player_by_dota_id(session: AsyncSession, dota_id: str) -> Player | None:
    result = await session.execute(select(Player).where(Player.dota_id == dota_id))
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
