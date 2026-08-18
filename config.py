import os

from dotenv import load_dotenv

load_dotenv()

_max_bot_token = os.getenv("BOT_TOKEN")
if not _max_bot_token:
    raise RuntimeError("BOT_TOKEN is not set")

_webhook_secret = os.getenv("WEBHOOK_SECRET")
if not _webhook_secret:
    raise RuntimeError("WEBHOOK_SECRET is not set")

MAX_BOT_TOKEN: str = _max_bot_token
MAX_API_URL = "https://platform-api2.max.ru"

WEBHOOK_SECRET: str = _webhook_secret
WEBHOOK_URL: str = "https://ovchuntonova.ru/max-helper/webhook"
