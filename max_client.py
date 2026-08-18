import ssl

import aiohttp

from config import MAX_API_URL


class MaxBot:
    def __init__(self, token: str):

        self.token = token
        self.session: aiohttp.ClientSession | None = None

    async def start(self):
        ssl_context = ssl.create_default_context()
        ssl_context.load_verify_locations(
            cafile=(
                "usr/local/share/ca-certificates/"
                "russian-trusted/"
                "russian_trusted_root_ca_pem.crt"
            )
        )

        connector = aiohttp.TCPConnector(ssl=ssl_context)

        self.session = aiohttp.ClientSession(
            connector=connector,
            headers={
                "Authorization": self.token,
            },
        )

    async def subscribe_webhook(
        self,
        url: str,
        secret: str,
    ):
        return await self.request(
            "POST",
            "/subscriptions",
            json={
                "url": url,
                "secret": secret,
            },
        )

    async def close(self):
        if self.session:
            await self.session.close()

    async def request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ):

        if self.session is None:
            raise RuntimeError("Max-HelperBot session is not started")

        async with self.session.request(
            method,
            f"{MAX_API_URL}{endpoint}",
            **kwargs,
        ) as response:
            response.raise_for_status()

            if response.status == 204:
                return None

            return await response.json()

    async def get_me(self):
        return await self.request(
            "GET",
            "/me",
        )
