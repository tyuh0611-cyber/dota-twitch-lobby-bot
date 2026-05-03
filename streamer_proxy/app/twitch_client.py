import httpx
from .config import settings
from .schemas import Chatter


class TwitchClient:
    base_url = 'https://api.twitch.tv/helix'

    async def get_chatters(self) -> list[Chatter]:
        if not all([settings.twitch_client_id, settings.twitch_access_token, settings.twitch_broadcaster_id, settings.twitch_moderator_id]):
            return []

        headers = {
            'Client-Id': settings.twitch_client_id,
            'Authorization': f'Bearer {settings.twitch_access_token}',
        }
        params = {
            'broadcaster_id': settings.twitch_broadcaster_id,
            'moderator_id': settings.twitch_moderator_id,
            'first': 1000,
        }
        chatters: list[Chatter] = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            while True:
                response = await client.get(f'{self.base_url}/chat/chatters', headers=headers, params=params)
                response.raise_for_status()
                payload = response.json()
                for item in payload.get('data', []):
                    chatters.append(Chatter(**item))
                cursor = payload.get('pagination', {}).get('cursor')
                if not cursor:
                    break
                params['after'] = cursor
        return chatters
