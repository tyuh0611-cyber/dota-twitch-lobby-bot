from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from .config import settings
from .crud import add_slots, blacklist_player, link_player, unblacklist_player
from .db import SessionLocal
from .models import Player
from .selection import select_next_player
from .twitch_proxy_client import streamer_proxy

router = Router()


def is_admin(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id in settings.admin_ids)


async def deny_if_not_admin(message: Message) -> bool:
    if not is_admin(message):
        await message.answer('Access denied')
        return True
    return False


@router.message(Command('start'))
async def start(message: Message) -> None:
    if await deny_if_not_admin(message):
        return
    await message.answer(
        'Dota Twitch Lobby Bot MVP\n\n'
        'Commands:\n'
        '/add DOTA_ID SLOTS\n'
        '/link DOTA_ID TWITCH_NAME STEAM_ID [DOTA_NAME]\n'
        '/next\n'
        '/lobby\n'
        '/players\n'
        '/invite STEAM_ID\n'
        '/blacklist DOTA_ID [reason]\n'
        '/unblacklist DOTA_ID'
    )


@router.message(Command('add'))
async def cmd_add(message: Message) -> None:
    if await deny_if_not_admin(message):
        return
    parts = message.text.split(maxsplit=2) if message.text else []
    if len(parts) < 3:
        await message.answer('Usage: /add DOTA_ID SLOTS')
        return
    dota_id, slots_raw = parts[1], parts[2]
    try:
        slots = int(slots_raw)
    except ValueError:
        await message.answer('SLOTS must be integer')
        return
    async with SessionLocal() as session:
        player = await add_slots(session, dota_id=dota_id, slots=slots, created_by=str(message.from_user.id))
    await message.answer(f'OK: {player.dota_id}\nslots_left: {player.slots_left}\nslots_total: {player.slots_total}')


@router.message(Command('link'))
async def cmd_link(message: Message) -> None:
    if await deny_if_not_admin(message):
        return
    parts = message.text.split(maxsplit=4) if message.text else []
    if len(parts) < 4:
        await message.answer('Usage: /link DOTA_ID TWITCH_NAME STEAM_ID [DOTA_NAME]')
        return
    dota_id = parts[1]
    twitch_name = parts[2]
    steam_id = parts[3]
    dota_name = parts[4] if len(parts) > 4 else None
    async with SessionLocal() as session:
        player = await link_player(session, dota_id, twitch_name, steam_id, dota_name)
    await message.answer(f'Linked:\nTwitch: {player.twitch_name}\nDota ID: {player.dota_id}\nSteam ID: {player.steam_id}\nDota name: {player.dota_name or "-"}')


@router.message(Command('players'))
async def cmd_players(message: Message) -> None:
    if await deny_if_not_admin(message):
        return
    async with SessionLocal() as session:
        result = await session.execute(select(Player).order_by(Player.slots_left.desc()).limit(20))
        players = result.scalars().all()
    if not players:
        await message.answer('No players yet')
        return
    lines = []
    for p in players:
        mark = 'BLACKLIST ' if p.is_blacklisted else ''
        lines.append(f'{mark}{p.dota_id} | {p.twitch_name or "-"} | slots: {p.slots_left} | played: {p.games_played}')
    await message.answer('\n'.join(lines))


@router.message(Command('lobby'))
async def cmd_lobby(message: Message) -> None:
    if await deny_if_not_admin(message):
        return
    try:
        lobby = await streamer_proxy.get_lobby()
    except Exception as exc:
        await message.answer(f'Proxy error: {exc}')
        return
    members = lobby.get('members', [])
    if not lobby.get('lobby_exists'):
        await message.answer('Lobby not found')
        return
    lines = [f'Lobby: {lobby.get("lobby_id")}', 'Members:']
    for m in members:
        lines.append(f'- {m.get("dota_name") or "-"} | dota: {m.get("dota_id") or "-"} | steam: {m.get("steam_id") or "-"}')
    await message.answer('\n'.join(lines))


@router.message(Command('next'))
async def cmd_next(message: Message) -> None:
    if await deny_if_not_admin(message):
        return
    try:
        chatters = await streamer_proxy.get_chatters()
    except Exception as exc:
        await message.answer(f'Proxy error: {exc}')
        return
    online_names = {c.get('user_login', '').lower() for c in chatters if c.get('user_login')}
    async with SessionLocal() as session:
        player = await select_next_player(session, online_names)
    if not player:
        await message.answer('No suitable player found. Use /invite STEAM_ID manually or add/link more players.')
        return
    await message.answer(
        'Next candidate:\n'
        f'Twitch: {player.twitch_name or "-"}\n'
        f'Dota name: {player.dota_name or "-"}\n'
        f'Dota ID: {player.dota_id}\n'
        f'Steam ID: {player.steam_id or "-"}\n'
        f'Slots left: {player.slots_left}\n'
        f'Games played: {player.games_played}\n\n'
        f'Invite: /invite {player.steam_id}' if player.steam_id else 'Steam ID missing. Use /link first.'
    )


@router.message(Command('invite'))
async def cmd_invite(message: Message) -> None:
    if await deny_if_not_admin(message):
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) < 2:
        await message.answer('Usage: /invite STEAM_ID')
        return
    steam_id = parts[1].strip()
    try:
        result = await streamer_proxy.invite(steam_id)
    except Exception as exc:
        await message.answer(f'Invite error: {exc}')
        return
    await message.answer(f'Invite result: {result}')


@router.message(Command('blacklist'))
async def cmd_blacklist(message: Message) -> None:
    if await deny_if_not_admin(message):
        return
    parts = message.text.split(maxsplit=2) if message.text else []
    if len(parts) < 2:
        await message.answer('Usage: /blacklist DOTA_ID [reason]')
        return
    async with SessionLocal() as session:
        player = await blacklist_player(session, parts[1], parts[2] if len(parts) > 2 else None)
    await message.answer('Blacklisted' if player else 'Player not found')


@router.message(Command('unblacklist'))
async def cmd_unblacklist(message: Message) -> None:
    if await deny_if_not_admin(message):
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) < 2:
        await message.answer('Usage: /unblacklist DOTA_ID')
        return
    async with SessionLocal() as session:
        player = await unblacklist_player(session, parts[1])
    await message.answer('Unblacklisted' if player else 'Player not found')


async def run_bot() -> None:
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)
