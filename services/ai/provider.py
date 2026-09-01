from config import OPENAI_API_KEY, OPENAI_MODEL
from services.ai.client import AIClient, OpenAIClient


_client: OpenAIClient | None = None


def configure_ai_client() -> OpenAIClient:
    global _client

    if _client is not None:
        return _client
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")
    if not OPENAI_MODEL:
        raise RuntimeError("OPENAI_MODEL is not set")

    _client = OpenAIClient(
        api_key=OPENAI_API_KEY,
        model=OPENAI_MODEL,
    )
    return _client


def get_ai_client() -> AIClient:
    return configure_ai_client()


async def shutdown_ai_client() -> None:
    global _client

    if _client is None:
        return
    await _client.close()
    _client = None
