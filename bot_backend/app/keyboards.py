from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def candidate_keyboard(steam_id: str | None, dota_id: str) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    if steam_id:
        buttons.append([InlineKeyboardButton(text='✅ Invite', callback_data=f'invite:{steam_id}')])
    buttons.append([
        InlineKeyboardButton(text='⏭ Next', callback_data='next_candidate'),
        InlineKeyboardButton(text='🚫 Blacklist', callback_data=f'blacklist:{dota_id}'),
    ])
    buttons.append([
        InlineKeyboardButton(text='➖ Charge -1', callback_data=f'charge:{dota_id}'),
        InlineKeyboardButton(text='👤 Manual ID', callback_data='manual_help'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def settings_keyboard(require_online: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f'Twitch online required: {"ON" if require_online else "OFF"}', callback_data='toggle_require_online')],
        [InlineKeyboardButton(text='🔄 Refresh candidate', callback_data='next_candidate')],
    ])
