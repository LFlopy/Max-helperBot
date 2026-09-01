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

_openai_api_key = os.getenv("OPENAI_API_KEY")
_openai_model = os.getenv("OPENAI_MODEL")

try:
    _free_history_limit = int(os.getenv("FREE_HISTORY_LIMIT", "10"))
except ValueError as error:
    raise RuntimeError("FREE_HISTORY_LIMIT must be an integer") from error

try:
    _trial_duration_days = int(os.getenv("TRIAL_DURATION_DAYS", "7"))
except ValueError as error:
    raise RuntimeError("TRIAL_DURATION_DAYS must be an integer") from error

try:
    _trial_history_limit = int(os.getenv("TRIAL_HISTORY_LIMIT", "25"))
except ValueError as error:
    raise RuntimeError("TRIAL_HISTORY_LIMIT must be an integer") from error

if _free_history_limit < 1:
    raise RuntimeError("FREE_HISTORY_LIMIT must be positive")
if _trial_duration_days < 1:
    raise RuntimeError("TRIAL_DURATION_DAYS must be positive")
if _trial_history_limit < 1:
    raise RuntimeError("TRIAL_HISTORY_LIMIT must be positive")

MAX_BOT_TOKEN: str = _max_bot_token
MAX_API_URL = "https://platform-api2.max.ru"

WEBHOOK_SECRET: str = _webhook_secret
WEBHOOK_URL: str = "https://ovchuntonova.ru/max-helper/webhook"

ADMIN_IDS = {int(user_id) for user_id in _admin_ids.split() if user_id.strip()}

DATABASE_URL: str = _database_url

OPENAI_API_KEY: str | None = _openai_api_key
OPENAI_MODEL: str | None = _openai_model

FREE_HISTORY_LIMIT: int = _free_history_limit
TRIAL_DURATION_DAYS: int = _trial_duration_days
TRIAL_HISTORY_LIMIT: int = _trial_history_limit
