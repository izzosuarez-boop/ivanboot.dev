"""Runtime settings, read from the environment (Docker env_file = repo .env)."""
from __future__ import annotations

import os


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip().strip("'\"")


SHOPIFY_SHOP = env("SHOPIFY_SHOP")
SHOPIFY_API_VERSION = env("SHOPIFY_API_VERSION", "2026-10")
SHOPIFY_STOREFRONT_PRIVATE_TOKEN = env("SHOPIFY_STOREFRONT_PRIVATE_TOKEN")
SHOPIFY_CLIENT_ID = env("SHOPIFY_CLIENT_ID")
SHOPIFY_CLIENT_SECRET = env("SHOPIFY_CLIENT_SECRET")  # also the key Shopify signs webhooks with (HMAC-SHA256)

# Owner bot (Telegram). The webhook secret is derived from the bot token so no extra variable is needed.
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN")
TELEGRAM_OWNER_CHAT_ID = env("TELEGRAM_OWNER_CHAT_ID")
LOW_STOCK_AT = int(env("LOW_STOCK_AT", "5"))
# Extra Telegram chats allowed to use the back-office bot (comma-separated chat ids); the owner is always allowed.
TELEGRAM_ALLOWED_CHAT_IDS = {c.strip() for c in env("TELEGRAM_ALLOWED_CHAT_IDS").split(",") if c.strip()}

ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
AGENT_MODEL = env("AGENT_MODEL", "claude-haiku-5-5")

SUPABASE_URL = env("SUPABASE_URL").rstrip("/")
SUPABASE_SECRET_KEY = env("SUPABASE_SECRET_KEY")

STORE_URL = env("STORE_URL", "https://tienda.ivanboot.dev")
UPWORK_URL = env("UPWORK_URL", "https://www.upwork.com/freelancers/~01d5ad771e5c598546")

# Budget and abuse limits for a public chat
DAILY_BUDGET_USD = float(env("AGENT_DAILY_BUDGET_USD", "2.0"))
MAX_MESSAGE_CHARS = 800
MAX_USER_TURNS = 24
RATE_PER_MINUTE = 10
RATE_PER_HOUR = 60
HASH_SALT = env("VISITOR_HASH_SALT", "ardea-demo")  # visitor IPs are stored only as salted hashes

# Claude Haiku 5.5 prices, USD per million tokens (prompts <= 100K tokens), checked 2026-11-20
PRICE_INPUT, PRICE_OUTPUT, PRICE_CACHE_READ, PRICE_CACHE_WRITE = 0.10, 0.50, 0.01, 0.125
