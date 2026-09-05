import ssl
from typing import Any
import aiohttp

from config import MAX_API_TIMEOUT_SECONDS, MAX_API_URL


class MaxBot:
    def __init__(self, token: str):

        self.token = token
        self.session: aiohttp.ClientSession | None = None

    async def start(self):
        ssl_context = ssl.create_default_context()
        ssl_context.load_verify_locations(
            cafile=(
                "/usr/local/share/ca-certificates/"
                "russian-trusted/"
                "russian_trusted_root_ca_pem.crt"
            )
        )

        connector = aiohttp.TCPConnector(ssl=ssl_context)

        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=MAX_API_TIMEOUT_SECONDS),
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
        **kwargs: Any,
    ) -> dict[str, Any] | None:

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

            data = await response.json()

            if not isinstance(data, dict):
                raise TypeError("MAX API returned unexpected response")

            return data

    async def get_me(self):
        return await self.request(
            "GET",
            "/me",
        )

    async def send_message(
        self,
        user_id: int,
        text: str,
        attachments: list | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "text": text,
        }

        if attachments is not None:
            payload["attachments"] = attachments

        result = await self.request(
            "POST",
            "/messages",
            params={
                "user_id": user_id,
            },
            json=payload,
        )

        if result is None:
            raise RuntimeError("MAX API returned an empty response")

        return result

    async def answer_callback(
        self,
        callback_id: str,
        message: dict,
    ) -> dict[str, Any]:
        result = await self.request(
                "POST",
                "/answers",
                params = {
                    "callback_id": callback_id,
                    },
                json = {
                    "message": message,
                    },
                )

        if result is None:
            raise RuntimeError("MAX API returned an empty response")
        return result
