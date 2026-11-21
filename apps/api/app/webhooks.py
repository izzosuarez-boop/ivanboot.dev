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

import anthropic

from . import config, db, guard, notify, owner_agent, reports, shopify, shopify_admin

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
        # one message per order doesn't scale: only big real orders now, the rest in the daily summary
        if "demo-seed" not in (payload.get("tags") or "") and float(payload.get("total_price") or 0) > config.BIG_ORDER_USD:
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
    if new != "ok" and not (new == "low" and old == "out"):  # going down only; restocks are not announced
        await notify.stock_alert(info["name"], info["total"])


# ── Telegram (owner commands) ────────────────────────────────────────────────────────────────────────

HELP = ("<b>Ardea Skin · back-office bot</b>\n"
        "Ask me anything about the store in plain words, for example:\n"
        "• <i>Chart of the best sellers of the last 3 months</i>\n"
        "• <i>Top 10 customers</i>\n"
        "• <i>How much did we sell this month vs last month?</i>\n"
        "• <i>What is running out of stock?</i>\n\n"
        "Shortcuts: /digest · /weekly · /stock · /orders · /stats · /new (forget this conversation)\n\n"
        "<b>What I send on my own</b>\n"
        "• Daily summary at 9:00 and a weekly report with charts on Mondays\n"
        "• Right away: sold out or under 10 units, orders over $150, and complaints, order issues or "
        "medical questions from the store chat")


def allowed(chat_id: str) -> bool:
    return chat_id == config.TELEGRAM_OWNER_CHAT_ID or chat_id in config.TELEGRAM_ALLOWED_CHAT_IDS


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
        tasks.add_task(_handle, chat_id, text)
    return {"ok": True}


async def _handle(chat_id: str, text: str) -> None:
    if not allowed(chat_id):
        await notify.telegram("This is a private bot for the Ardea Skin store team.", chat_id)
        return
    cmd = text.split()[0].split("@")[0].lower() if text.startswith("/") else ""
    try:
        if cmd in ("/start", "/help", "/new"):
            owner_agent.reset(chat_id)
            await notify.telegram(HELP if cmd != "/new" else "🧹 Fresh start — ask me anything.", chat_id)
        elif cmd == "/stock":
            await notify.telegram(await _stock_report(), chat_id)
        elif cmd == "/orders":
            await notify.telegram(await _orders_report(), chat_id)
        elif cmd == "/stats":
            await notify.telegram(await _stats_report(), chat_id)
        elif cmd == "/digest":
            await notify.typing(chat_id)
            await reports.send_daily(chat_id)
        elif cmd == "/weekly":
            await notify.typing(chat_id, "upload_photo")
            await reports.send_weekly(chat_id)
        elif cmd:
            await notify.telegram(HELP, chat_id)
        else:
            await _ask(chat_id, text)
    except Exception as e:  # noqa: BLE001
        log.warning("telegram %s failed: %s", cmd or "question", e.__class__.__name__)
        await notify.telegram("Couldn't fetch that right now — try again in a minute.", chat_id)


async def _ask(chat_id: str, text: str) -> None:
    if not config.ANTHROPIC_API_KEY:
        await notify.telegram("The AI assistant isn't configured. The shortcuts /stock /orders /stats still work.", chat_id)
        return
    if await guard.over_budget():
        await notify.telegram("Today's AI budget is used up. Shortcuts /stock /orders /stats still work.", chat_id)
        return
    await notify.typing(chat_id)
    try:
        reply, photos, cost = await owner_agent.ask(chat_id, text)
    except anthropic.APIError as e:
        log.warning("owner agent: %s", e.__class__.__name__)
        await notify.telegram("The assistant had a hiccup — please try again.", chat_id)
        return
    await notify.telegram(reply, chat_id)
    for png, _ in photos:
        await notify.typing(chat_id, "upload_photo")
        await notify.telegram_photo(png, chat_id)
    log.info("owner question answered: %d chart(s), $%.5f", len(photos), cost)


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
