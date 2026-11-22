"""One-time setup of the owner's Telegram bot.

    python scripts/telegram/setup_bot.py           # find owner chat id (message the bot first), save it to .env
    python scripts/telegram/setup_bot.py --webhook # point the bot at https://api.ivanboot.dev/webhooks/telegram

The chat id comes from getUpdates, which only works while no webhook is set, so run the plain step first.
The webhook secret is derived from the bot token exactly like apps/api/app/webhooks.py:telegram_secret().
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import httpx

sys.stdout.reconfigure(encoding="utf-8")
ENV = Path(__file__).resolve().parents[2] / ".env"
WEBHOOK_URL = "https://api.ivanboot.dev/webhooks/telegram"
COMMANDS = [{"command": "digest", "description": "Yesterday's summary"},
            {"command": "weekly", "description": "Last 7 days with charts"},
            {"command": "stock", "description": "Low-stock and sold-out products"},
            {"command": "orders", "description": "Last 5 orders"},
            {"command": "stats", "description": "AI chat usage and spend"},
            {"command": "help", "description": "What this bot does"}]


def env_values() -> dict[str, str]:
    out = {}
    for line in ENV.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$", line)
        if m:
            out[m.group(1)] = m.group(2).strip("'\"")
    return out


def set_env(key: str, value: str) -> None:
    text = ENV.read_text(encoding="utf-8")
    if re.search(rf"^{key}\s*=.*$", text, flags=re.M):
        text = re.sub(rf"^{key}\s*=.*$", f"{key}={value}", text, flags=re.M)
    else:
        text = text.rstrip("\n") + f"\n{key}={value}\n"
    ENV.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    env = env_values()
    token = env.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN missing in .env")
    api = f"https://api.telegram.org/bot{token}"
    me = httpx.get(f"{api}/getMe", timeout=15).json()
    print("bot:", "@" + me["result"]["username"])

    if "--webhook" in sys.argv:
        secret = hashlib.sha256(f"ardea-owner-bot:{token}".encode()).hexdigest()[:48]
        r = httpx.post(f"{api}/setWebhook", timeout=15, json={
            "url": WEBHOOK_URL, "secret_token": secret, "allowed_updates": ["message", "callback_query"],  # buttons
            "drop_pending_updates": True})
        print("setWebhook:", r.json().get("description"))
        print("setMyCommands:", httpx.post(f"{api}/setMyCommands", json={"commands": COMMANDS}, timeout=15).json().get("ok"))
        info = httpx.get(f"{api}/getWebhookInfo", timeout=15).json()["result"]
        print("webhook:", info.get("url"), "| pending:", info.get("pending_update_count"), "| last error:", info.get("last_error_message"))
        return 0

    updates = httpx.get(f"{api}/getUpdates", timeout=15).json()
    if not updates.get("ok"):
        raise SystemExit(f"getUpdates failed (is a webhook already set?): {updates.get('description')}")
    chats = {}
    for u in updates["result"]:
        chat = (u.get("message") or {}).get("chat") or {}
        if chat.get("type") == "private":
            chats[chat["id"]] = chat.get("first_name", "")
    if len(chats) != 1:
        raise SystemExit(f"Expected exactly 1 private chat with the bot, found {len(chats)}. "
                         "Open the bot in Telegram, press Start and send any message, then run again.")
    chat_id, name = next(iter(chats.items()))
    set_env("TELEGRAM_OWNER_CHAT_ID", str(chat_id))
    print(f"owner chat found ({name}); saved TELEGRAM_OWNER_CHAT_ID to .env")
    return 0


if __name__ == "__main__":
    sys.exit(main())
