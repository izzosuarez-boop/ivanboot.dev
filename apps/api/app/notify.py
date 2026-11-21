"""Owner notifications over Telegram: chat escalations, new orders, low stock and sell-outs.

No-op until TELEGRAM_BOT_TOKEN and TELEGRAM_OWNER_CHAT_ID are set (escalations are still stored in Supabase).
Messages use Telegram's HTML mode; every dynamic value goes through esc().
"""
from __future__ import annotations

import html
import logging
from datetime import datetime, timezone

import httpx

from . import config, db

log = logging.getLogger("agent.notify")
LABELS = {"complaint": "Complaint", "order_issue": "Order issue", "medical_question": "Medical question",
          "human_request": "Wants a human", "other": "Other"}
ICONS = {"complaint": "⚠️", "order_issue": "📦", "medical_question": "🩺", "human_request": "🙋", "other": "💬"}


def esc(v) -> str:
    return html.escape(str(v), quote=False)


def enabled() -> bool:
    return bool(config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_OWNER_CHAT_ID)


async def telegram(text: str, chat_id: str | int | None = None) -> bool:
    chat_id = chat_id or config.TELEGRAM_OWNER_CHAT_ID
    if not config.TELEGRAM_BOT_TOKEN or not chat_id:
        return False
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            r = await http.post(f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage",
                                json={"chat_id": chat_id, "text": text[:4000], "parse_mode": "HTML",
                                      "disable_web_page_preview": True})
        if r.status_code != 200:
            log.warning("telegram %s: %s", r.status_code, r.text[:200])
        return r.status_code == 200
    except httpx.HTTPError as e:
        log.warning("telegram failed: %s", e)
        return False


async def owner_escalation(row: dict) -> bool:
    kind = row.get("kind") or "other"
    text = (f"{ICONS.get(kind, '💬')} <b>{esc(LABELS.get(kind, 'Case'))}</b> · <code>{esc(row.get('ref_code'))}</code>\n"
            f"From the store chat:\n\n{esc(row.get('summary'))}"
            + (f"\n\nContact: {esc(row['contact'])}" if row.get("contact") else ""))
    sent = await telegram(text)
    if sent and row.get("ref_code"):
        await db.update(f"escalations?ref_code=eq.{row['ref_code']}",
                        {"status": "notified", "notified_at": datetime.now(timezone.utc).isoformat()})
    return sent


async def new_order(order: dict) -> bool:
    items = "\n".join(f"• {esc(li.get('quantity'))}× {esc(li.get('title'))}"
                      + (f" ({esc(li['variant_title'])})" if li.get("variant_title") else "")
                      for li in order.get("line_items") or [])
    test = " · test order" if order.get("test") else ""
    admin = f"https://admin.shopify.com/store/{config.SHOPIFY_SHOP}/orders/{order.get('id')}"
    return await telegram(f"🛍 <b>New order {esc(order.get('name'))}</b>{test}\n"
                          f"{esc(order.get('total_price'))} {esc(order.get('currency'))}\n\n{items}\n\n"
                          f'<a href="{esc(admin)}">Open in Shopify</a>')


async def stock_alert(name: str, qty: int) -> bool:
    if qty <= 0:
        return await telegram(f"⛔ <b>Sold out:</b> {esc(name)}\nIt now shows as sold out in the store.")
    return await telegram(f"📉 <b>Low stock:</b> {esc(name)} — {qty} left")
