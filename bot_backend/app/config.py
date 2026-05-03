from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    telegram_bot_token: str
    telegram_admin_ids: str = ''
    database_url: str
    streamer_proxy_url: str
    streamer_proxy_api_key: str
    require_twitch_online: bool = True
    special_first_twitch_names: str = ''
    invite_timeout_seconds: int = 60

    @property
    def admin_ids(self) -> set[int]:
        return {int(x.strip()) for x in self.telegram_admin_ids.split(',') if x.strip()}

    @property
    def special_names(self) -> set[str]:
        return {x.strip().lower() for x in self.special_first_twitch_names.split(',') if x.strip()}


settings = Settings()
