from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from .config import settings
from .crud import (
    add_slots,
    blacklist_player,
    charge_slot_after_game,
    link_player,
    recent_slot_logs,
    set_comment,
    set_slots,
    unblacklist_player,
)
from .db import SessionLocal
from .keyboards import candidate_keyboard, settings_keyboard
from .models import Player
from .selection import select_next_player
from .twitch_proxy_client import streamer_proxy

router = Router()
_runtime_settings = {'require_twitch_online': settings.require_twitch_online}


def is_admin_user(user_id: int | None) -> bool:
    return bool(user_id and user_id in settings.admin_ids)


def is_admin(message: Message) -> bool:
    return bool(message.from_user and is_admin_user(message.from_user.id))


async def deny_if_not_admin(message: Message) -> bool:
    if not is_admin(message):
        await message.answer('Access denied')
        return True
    return False


async def deny_callback_if_not_admin(callback: CallbackQuery) -> bool:
    if not is_admin_user(callback.from_user.id if callback.from_user else None):
        await callback.answer('Access denied', show_alert=True)
        return True
    return False


async def build_next_candidate_message() -> tuple[str, object | None]:
    chatters = await streamer_proxy.get_chatters()
    online_names = {c.get('user_login', '').lower() for c in chatters if c.get('user_login')}
    async with SessionLocal() as session:
        player = await select_next_player(session, online_names)
    if not player:
        return 'No suitable player found. Use /invite STEAM_ID manually or add/link more players.', None
    text = (
        'Next candidate:\n'
        f'Twitch: {player.twitch_name or "-"}\n'
        f'Dota name: {player.dota_name or "-"}\n'
        f'Dota ID: {player.dota_id}\n'
        f'Steam ID: {player.steam_id or "-"}\n'
        f'Slots left: {player.slots_left}\n'
        f'Games played: {player.games_played}\n'
        f'Comment: {player.comment or "-"}'
    )
    return text, candidate_keyboard(player.steam_id, player.dota_id)


@router.message(Command('start'))
async def start(message: Message) -> None:
    if await deny_if_not_admin(message):
        return
    await message.answer(
        'Dota Twitch Lobby Bot MVP\n\n'
        'Main commands:\n'
        '/add DOTA_ID SLOTS\n'
        '/setslots DOTA_ID SLOTS\n'
        '/link DOTA_ID TWITCH_NAME STEAM_ID [DOTA_NAME]\n'
        '/next\n'
        '/lobby\n'
        '/players\n'
        '/invite STEAM_ID\n'
        '/charge DOTA_ID\n'
        '/comment DOTA_ID text\n'
        '/history DOTA_ID\n'
        '/blacklist DOTA_ID [reason]\n'
        '/unblacklist DOTA_ID\n'
        '/settings'
    )


@router.message(Command('add'))
async def cmd_add(message: Message) -> None:
    if await deny_if_not_admin(message):
        return
    parts = message.text.split(maxsplit=2) if message.text else []
    if len(parts) < 3:
        await message.answer('Usage: /add DOTA_ID SLOTS')
        return
    try:
        slots = int(parts[2])
    except ValueError:
        await message.answer('SLOTS must be integer')
        return
    async with SessionLocal() as session:
        player = await add_slots(session, dota_id=parts[1], slots=slots, created_by=str(message.from_user.id))
    await message.answer(f'OK: {player.dota_id}\nslots_left: {player.slots_left}\nslots_total: {player.slots_total}')


@router.message(Command('setslots'))
async def cmd_setslots(message: Message) -> None:
    if await deny_if_not_admin(message):
        return
    parts = message.text.split(maxsplit=2) if message.text else []
    if len(parts) < 3:
        await message.answer('Usage: /setslots DOTA_ID SLOTS')
        return
    try:
        slots = int(parts[2])
    except ValueError:
        await message.answer('SLOTS must be integer')
        return
    async with SessionLocal() as session:
        player = await set_slots(session, parts[1], slots, created_by=str(message.from_user.id))
    await message.answer(f'Slots set: {player.dota_id}\nslots_left: {player.slots_left}')


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
        result = await session.execute(select(Player).order_by(Player.slots_left.desc()).limit(30))
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
        text, keyboard = await build_next_candidate_message()
    except Exception as exc:
        await message.answer(f'Proxy error: {exc}')
        return
    await message.answer(text, reply_markup=keyboard)


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


@router.message(Command('charge'))
async def cmd_charge(message: Message) -> None:
    if await deny_if_not_admin(message):
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) < 2:
        await message.answer('Usage: /charge DOTA_ID')
        return
    async with SessionLocal() as session:
        player = await charge_slot_after_game(session, parts[1], created_by=str(message.from_user.id))
    if not player:
        await message.answer('Player not found')
        return
    await message.answer(f'Charged after game:\n{player.dota_id}\nslots_left: {player.slots_left}\ngames_played: {player.games_played}')


@router.message(Command('comment'))
async def cmd_comment(message: Message) -> None:
    if await deny_if_not_admin(message):
        return
    parts = message.text.split(maxsplit=2) if message.text else []
    if len(parts) < 3:
        await message.answer('Usage: /comment DOTA_ID text')
        return
    async with SessionLocal() as session:
        player = await set_comment(session, parts[1], parts[2])
    await message.answer('Comment saved' if player else 'Player not found')


@router.message(Command('history'))
async def cmd_history(message: Message) -> None:
    if await deny_if_not_admin(message):
        return
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) < 2:
        await message.answer('Usage: /history DOTA_ID')
        return
    async with SessionLocal() as session:
        logs = await recent_slot_logs(session, parts[1], limit=10)
    if not logs:
        await message.answer('No history')
        return
    await message.answer('\n'.join(f'{log.created_at}: {log.old_slots_left} -> {log.new_slots_left} ({log.reason})' for log in logs))


@router.message(Command('settings'))
async def cmd_settings(message: Message) -> None:
    if await deny_if_not_admin(message):
        return
    await message.answer('Settings:', reply_markup=settings_keyboard(_runtime_settings['require_twitch_online']))


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


@router.callback_query()
async def callbacks(callback: CallbackQuery) -> None:
    if await deny_callback_if_not_admin(callback):
        return
    data = callback.data or ''
    if data == 'next_candidate':
        text, keyboard = await build_next_candidate_message()
        await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        return
    if data == 'manual_help':
        await callback.message.answer('Manual invite: /invite STEAM_ID')
        await callback.answer()
        return
    if data == 'toggle_require_online':
        _runtime_settings['require_twitch_online'] = not _runtime_settings['require_twitch_online']
        await callback.message.answer('Changed for current runtime only.', reply_markup=settings_keyboard(_runtime_settings['require_twitch_online']))
        await callback.answer()
        return
    if data.startswith('invite:'):
        steam_id = data.split(':', 1)[1]
        result = await streamer_proxy.invite(steam_id)
        await callback.message.answer(f'Invite result: {result}')
        await callback.answer()
        return
    if data.startswith('blacklist:'):
        dota_id = data.split(':', 1)[1]
        async with SessionLocal() as session:
            await blacklist_player(session, dota_id, 'from_button')
        await callback.message.answer(f'Blacklisted: {dota_id}')
        await callback.answer()
        return
    if data.startswith('charge:'):
        dota_id = data.split(':', 1)[1]
        async with SessionLocal() as session:
            player = await charge_slot_after_game(session, dota_id, created_by=str(callback.from_user.id))
        await callback.message.answer(f'Charged: {dota_id}, slots_left: {player.slots_left if player else "not found"}')
        await callback.answer()
        return
    await callback.answer('Unknown action')


async def run_bot() -> None:
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)
