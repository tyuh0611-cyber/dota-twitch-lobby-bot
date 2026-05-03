import httpx
from .config import settings


class StreamerProxyClient:
    def __init__(self) -> None:
        self.base_url = settings.streamer_proxy_url.rstrip('/')
        self.headers = {'X-Api-Key': settings.streamer_proxy_api_key}

    async def get_chatters(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f'{self.base_url}/chatters', headers=self.headers)
            response.raise_for_status()
            return response.json().get('data', [])

    async def get_lobby(self) -> dict:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f'{self.base_url}/dota/lobby', headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def invite(self, steam_id: str) -> dict:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(f'{self.base_url}/dota/invite', headers=self.headers, json={'steam_id': steam_id})
            response.raise_for_status()
            return response.json()


streamer_proxy = StreamerProxyClient()
