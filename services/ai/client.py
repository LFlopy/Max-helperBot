from collections.abc import Sequence
from typing import Protocol

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
)
from openai.types.responses import ResponseInputItemParam

from services.ai.models import AIMessage


class AIClientError(Exception):
    pass


class AIClient(Protocol):
    async def generate(
        self,
        system_prompt: str,
        messages: Sequence[AIMessage],
    ) -> str: ...


class OpenAIClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout: float = 30.0,
    ) -> None:
        self.model = model
        self.client = AsyncOpenAI(
            api_key=api_key,
            timeout=timeout,
        )

    async def generate(
        self,
        system_prompt: str,
        messages: Sequence[AIMessage],
    ) -> str:
        input_messages: list[ResponseInputItemParam] = [
            {
                "role": message.role,
                "content": message.content,
            }
            for message in messages
        ]

        try:
            response = await self.client.responses.create(
                model=self.model,
                instructions=system_prompt,
                input=input_messages,
                store=False,
            )
        except (APIConnectionError, APIStatusError, APITimeoutError) as error:
            raise AIClientError("OpenAI request failed") from error

        content = response.output_text.strip()
        if not content:
            raise AIClientError("OpenAI returned an empty response")
        return content

    async def close(self) -> None:
        await self.client.close()
