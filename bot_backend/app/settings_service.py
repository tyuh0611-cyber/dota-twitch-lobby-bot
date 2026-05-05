from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .config import settings as env_settings
from .models import BotSetting

DEFAULTS = {
    'require_twitch_online': str(env_settings.require_twitch_online).lower(),
    'special_first_twitch_names': env_settings.special_first_twitch_names,
    'queue_strategy': 'oldest_played',
    'invite_timeout_seconds': str(env_settings.invite_timeout_seconds),
}


async def get_setting(session: AsyncSession, key: str) -> str:
    row = await session.get(BotSetting, key)
    if row is None:
        return DEFAULTS.get(key, '')
    return row.value


async def set_setting(session: AsyncSession, key: str, value: str) -> None:
    row = await session.get(BotSetting, key)
    if row is None:
        session.add(BotSetting(key=key, value=value))
    else:
        row.value = value
    await session.commit()


async def get_all_settings(session: AsyncSession) -> dict[str, str]:
    result = await session.execute(select(BotSetting))
    stored = {row.key: row.value for row in result.scalars().all()}
    merged = dict(DEFAULTS)
    merged.update(stored)
    return merged


def setting_bool(value: str) -> bool:
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def split_names(value: str) -> set[str]:
    return {item.strip().lower() for item in value.split(',') if item.strip()}
