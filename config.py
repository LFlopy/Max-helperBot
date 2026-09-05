import os

from dotenv import load_dotenv

load_dotenv()


def _parse_bool(value: str, name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{name} must be a boolean")

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
_payment_provider = os.getenv("PAYMENT_PROVIDER", "disabled").strip().lower()
_sqlalchemy_echo = _parse_bool(
    os.getenv("SQLALCHEMY_ECHO", "false"),
    "SQLALCHEMY_ECHO",
)

try:
    _max_api_timeout_seconds = float(
        os.getenv("MAX_API_TIMEOUT_SECONDS", "15")
    )
except ValueError as error:
    raise RuntimeError("MAX_API_TIMEOUT_SECONDS must be a number") from error

try:
    _broadcast_send_interval_seconds = float(
        os.getenv("BROADCAST_SEND_INTERVAL_SECONDS", "0.05")
    )
    _broadcast_retry_backoff_seconds = float(
        os.getenv("BROADCAST_RETRY_BACKOFF_SECONDS", "1")
    )
except ValueError as error:
    raise RuntimeError("Broadcast timing settings must be numbers") from error

try:
    _broadcast_max_attempts = int(os.getenv("BROADCAST_MAX_ATTEMPTS", "3"))
except ValueError as error:
    raise RuntimeError("BROADCAST_MAX_ATTEMPTS must be an integer") from error

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
if _max_api_timeout_seconds <= 0:
    raise RuntimeError("MAX_API_TIMEOUT_SECONDS must be positive")
if _broadcast_send_interval_seconds < 0:
    raise RuntimeError("BROADCAST_SEND_INTERVAL_SECONDS cannot be negative")
if _broadcast_retry_backoff_seconds < 0:
    raise RuntimeError("BROADCAST_RETRY_BACKOFF_SECONDS cannot be negative")
if _broadcast_max_attempts < 1:
    raise RuntimeError("BROADCAST_MAX_ATTEMPTS must be positive")
if _payment_provider not in {"disabled", "fake"}:
    raise RuntimeError("PAYMENT_PROVIDER must be disabled or fake")

MAX_BOT_TOKEN: str = _max_bot_token
MAX_API_URL = "https://platform-api2.max.ru"
MAX_API_TIMEOUT_SECONDS: float = _max_api_timeout_seconds
BROADCAST_SEND_INTERVAL_SECONDS: float = _broadcast_send_interval_seconds
BROADCAST_RETRY_BACKOFF_SECONDS: float = _broadcast_retry_backoff_seconds
BROADCAST_MAX_ATTEMPTS: int = _broadcast_max_attempts

WEBHOOK_SECRET: str = _webhook_secret
WEBHOOK_URL: str = "https://ovchuntonova.ru/max-helper/webhook"

ADMIN_IDS = {int(user_id) for user_id in _admin_ids.split() if user_id.strip()}

DATABASE_URL: str = _database_url

OPENAI_API_KEY: str | None = _openai_api_key
OPENAI_MODEL: str | None = _openai_model
PAYMENT_PROVIDER: str = _payment_provider

FREE_HISTORY_LIMIT: int = _free_history_limit
TRIAL_DURATION_DAYS: int = _trial_duration_days
TRIAL_HISTORY_LIMIT: int = _trial_history_limit
SQLALCHEMY_ECHO: bool = _sqlalchemy_echo
