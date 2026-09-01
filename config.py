import os

from dotenv import load_dotenv

load_dotenv()

_max_bot_token = os.getenv("BOT_TOKEN")
if not _max_bot_token:
    raise RuntimeError("BOT_TOKEN is not set")

_webhook_secret = os.getenv("WEBHOOK_SECRET")
if not _webhook_secret:
    raise RuntimeError("WEBHOOK_SECRET is not set")

_admin_ids = os.getenv("ADMIN_IDS")
if not _admin_ids:
    raise RuntimeError("ADMIN_IDS is not set")

_database_url = os.getenv("DATABASE_URL")
if not _database_url:
    raise RuntimeError("DATABASE_URL is not set")

MAX_BOT_TOKEN: str = _max_bot_token
MAX_API_URL = "https://platform-api2.max.ru"

WEBHOOK_SECRET: str = _webhook_secret
WEBHOOK_URL: str = "https://ovchuntonova.ru/max-helper/webhook"

ADMIN_IDS = {int(user_id) for user_id in _admin_ids.split() if user_id.strip()}

DATABASE_URL: str = _database_url
