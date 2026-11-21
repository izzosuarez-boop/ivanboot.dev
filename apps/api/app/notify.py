"""Owner notifications. Telegram arrives in the next step; until TELEGRAM_BOT_TOKEN and
TELEGRAM_OWNER_CHAT_ID are set this is a no-op (the escalation is still stored in Supabase)."""
from __future__ import annotations

import logging

import httpx

from .config import env

log = logging.getLogger("agent.notify")
LABELS = {"complaint": "Complaint", "order_issue": "Order issue", "medical_question": "Medical question",
          "human_request": "Wants a human", "other": "Other"}


async def telegram(text: str) -> bool:
    token, chat_id = env("TELEGRAM_BOT_TOKEN"), env("TELEGRAM_OWNER_CHAT_ID")
    if not token or not chat_id:
        return False
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            r = await http.post(f"https://api.telegram.org/bot{token}/sendMessage",
                                json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True})
        return r.status_code == 200
    except httpx.HTTPError as e:
        log.warning("telegram failed: %s", e)
        return False


async def owner_escalation(row: dict) -> bool:
    text = (f"🧴 Ardea Skin — {LABELS.get(row.get('kind'), 'Case')} {row.get('ref_code')}\n\n{row.get('summary')}"
            + (f"\n\nContact: {row['contact']}" if row.get("contact") else ""))
    return await telegram(text)
