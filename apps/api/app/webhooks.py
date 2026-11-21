"""Inbound webhooks: Shopify (orders, inventory) → Telegram alerts, and the owner's Telegram commands.

Shopify:  POST /webhooks/shopify   — verified with HMAC-SHA256 of the raw body (key: app client secret).
Telegram: POST /webhooks/telegram  — verified with the secret_token header set by setWebhook; only the
          owner's chat id gets answers.
Both reply 200 at once and do the work in a background task, so the senders never time out or retry.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time

from fastapi import APIRouter, BackgroundTasks, Request, Response

from . import config, db, guard, notify, shopify, shopify_admin

log = logging.getLogger("webhooks")
router = APIRouter(prefix="/webhooks")

_SEEN: dict[str, float] = {}           # Shopify delivers at-least-once: drop repeats by webhook id
_STOCK_STATE: dict[str, str] = {}      # inventory item id -> "ok" | "low" | "out" (alert only on changes)


def telegram_secret() -> str:
    """Secret for Telegram's X-Telegram-Bot-Api-Secret-Token header, derived from the bot token."""
    return hashlib.sha256(f"ardea-owner-bot:{config.TELEGRAM_BOT_TOKEN}".encode()).hexdigest()[:48]


def valid_shopify_hmac(body: bytes, header: str) -> bool:
    if not config.SHOPIFY_CLIENT_SECRET or not header:
        return False
    digest = hmac.new(config.SHOPIFY_CLIENT_SECRET.encode(), body, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(digest).decode(), header)


def _first_time(webhook_id: str) -> bool:
    now = time.time()
    for k in [k for k, t in _SEEN.items() if now - t > 86400]:
        del _SEEN[k]
    if not webhook_id or webhook_id in _SEEN:
        return not webhook_id
    _SEEN[webhook_id] = now
    return True


def _level(qty: int) -> str:
    return "out" if qty <= 0 else "low" if qty <= config.LOW_STOCK_AT else "ok"


# ── Shopify ──────────────────────────────────────────────────────────────────────────────────────────

@router.post("/shopify")
async def shopify_webhook(request: Request, tasks: BackgroundTasks):
    body = await request.body()
    if not valid_shopify_hmac(body, request.headers.get("x-shopify-hmac-sha256", "")):
        return Response(status_code=401)
    if not _first_time(request.headers.get("x-shopify-webhook-id", "")):
        return {"ok": True, "duplicate": True}
    topic = request.headers.get("x-shopify-topic", "")
    payload = json.loads(body or b"{}")
    if topic == "orders/create":
        tasks.add_task(notify.new_order, payload)
    elif topic == "inventory_levels/update":
        tasks.add_task(_inventory_changed, payload)
    log.info("shopify webhook %s", topic)
    return {"ok": True}


async def _inventory_changed(payload: dict) -> None:
    item_id = str(payload.get("inventory_item_id", ""))
    try:
        info = await shopify_admin.inventory_item(item_id)
        live = await shopify.catalog()
    except Exception as e:  # noqa: BLE001 — a failed lookup must not break the webhook
        log.warning("inventory lookup %s failed: %s", item_id, e)
        return
    if not info or info["handle"] not in live:  # retired products are no longer sold: stay quiet
        return
    new, old = _level(info["total"]), _STOCK_STATE.get(item_id)
    _STOCK_STATE[item_id] = new
    if new == old:
        return
    if new != "ok":
        await notify.stock_alert(info["name"], info["total"])
    elif old in ("low", "out"):
        await notify.telegram(f"✅ <b>Restocked:</b> {notify.esc(info['name'])} — {info['total']} available")


# ── Telegram (owner commands) ────────────────────────────────────────────────────────────────────────

HELP = ("<b>Ardea Skin · owner bot</b>\n"
        "/stock — low-stock and sold-out products\n"
        "/orders — last 5 orders\n"
        "/stats — AI chat usage and spend\n\n"
        "You also get alerts for new orders, low stock, sell-outs and chat escalations.")


@router.post("/telegram")
async def telegram_webhook(request: Request, tasks: BackgroundTasks):
    if not config.TELEGRAM_BOT_TOKEN or not hmac.compare_digest(
            request.headers.get("x-telegram-bot-api-secret-token", ""), telegram_secret()):
        return Response(status_code=401)
    update = await request.json()
    msg = update.get("message") or {}
    chat_id = str((msg.get("chat") or {}).get("id", ""))
    text = (msg.get("text") or "").strip()
    if chat_id and text:
        tasks.add_task(_command, chat_id, text)
    return {"ok": True}


async def _command(chat_id: str, text: str) -> None:
    if chat_id != config.TELEGRAM_OWNER_CHAT_ID:
        await notify.telegram("This is a private bot for the Ardea Skin store owner.", chat_id)
        return
    cmd = text.split()[0].split("@")[0].lower()
    try:
        if cmd == "/stock":
            reply = await _stock_report()
        elif cmd == "/orders":
            reply = await _orders_report()
        elif cmd == "/stats":
            reply = await _stats_report()
        else:
            reply = HELP
    except Exception as e:  # noqa: BLE001
        log.warning("command %s failed: %s", cmd, e)
        reply = "Couldn't fetch that right now — try again in a minute."
    await notify.telegram(reply, chat_id)


async def _stock_report() -> str:
    live = await shopify.catalog()
    rows = sorted((v for v in await shopify_admin.stock_levels() if v["handle"] in live), key=lambda v: v["qty"])
    out = [f"⛔ {notify.esc(v['name'])}" for v in rows if v["qty"] <= 0]
    low = [f"📉 {notify.esc(v['name'])} — {v['qty']}" for v in rows if 0 < v["qty"] <= config.LOW_STOCK_AT]
    if not out and not low:
        return f"✅ All {len(rows)} variants have more than {config.LOW_STOCK_AT} units."
    return "<b>Stock to watch</b>\n" + "\n".join(out + low) + f"\n\n{len(rows)} variants on sale in total."


async def _orders_report() -> str:
    orders = await shopify_admin.recent_orders(5)
    if not orders:
        return "No orders yet."
    lines = [f"<b>{notify.esc(o['name'])}</b> · {notify.esc(o['total'])} · {notify.esc(o['status'].lower())}"
             + (" · test" if o["test"] else "") + f"\n{notify.esc(o['created'][:16].replace('T', ' '))} UTC\n"
             + "\n".join(f"  {notify.esc(i)}" for i in o["items"]) for o in orders]
    return "<b>Last orders</b>\n\n" + "\n\n".join(lines)


async def _stats_report() -> str:
    s = await db.rpc("agent_stats") or {}
    today = await guard.spent_today()
    return ("<b>AI chat</b>\n"
            f"Conversations: {s.get('conversations_total', 0)} ({s.get('conversations_today', 0)} today)\n"
            f"Visitor messages: {s.get('visitor_messages_total', 0)}\n"
            f"Spend: ${today:.4f} today · ${s.get('spend_usd_total', 0)} total (cap ${config.DAILY_BUDGET_USD:.2f}/day)\n"
            f"Avg per conversation: ${s.get('avg_cost_per_conversation_usd', 0)}")
