"""Restocking from Telegram: the owner bot's only write action.

The model can only PROPOSE a change (propose()). Nothing touches Shopify until the owner taps Confirm on the
message's inline button (confirm()). Guard rails:
  - only the owner's chat (TELEGRAM_OWNER_CHAT_ID) may propose or confirm;
  - at most MAX_UNITS units per change and MAX_STOCK units in total;
  - proposals expire after TTL and belong to the chat that made them;
  - the write is a compare-and-swap: if the stock moved since the proposal, Shopify rejects it;
  - the result is read back from Shopify, the store cache is refreshed, and every attempt is logged.
"""
from __future__ import annotations

import logging
import re
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from . import config, db, notify, shopify, shopify_admin, web_cache

log = logging.getLogger("restock")
MAX_UNITS = 500
MAX_STOCK = 2000
TTL = 600  # seconds a proposal stays valid


@dataclass
class Proposal:
    chat_id: str
    name: str
    handle: str
    item_id: str
    location_id: str
    from_qty: int
    to_qty: int
    created: float


_PENDING: dict[str, Proposal] = {}


def _words(s: str) -> set[str]:
    return {w for w in re.split(r"[^a-z0-9%.]+", s.lower()) if w and w not in {"the", "of", "de", "la", "el", "-"}}


def _match(query: str, variants: list[dict]) -> list[dict]:
    """Exact name first, then variants containing every word of the query, then the best word overlap."""
    q = query.strip().lower()
    exact = [v for v in variants if v["name"].lower() == q]
    if exact:
        return exact
    words = _words(query)
    full = [v for v in variants if words and words <= _words(v["name"])]
    if full:
        return full
    scored = sorted(((len(words & _words(v["name"])), v) for v in variants), key=lambda t: t[0], reverse=True)
    best = scored[0][0] if scored else 0
    return [v for s, v in scored if s == best and s > 0]


def _clean() -> None:
    now = time.time()
    for k in [k for k, p in _PENDING.items() if now - p.created > TTL]:
        del _PENDING[k]


async def propose(chat_id: str, product: str, units: int, mode: str = "add") -> tuple[dict, str | None]:
    """Returns (result for the model, proposal id or None). Never writes to Shopify."""
    if chat_id != config.TELEGRAM_OWNER_CHAT_ID:
        return {"error": "Only the store owner can change stock."}, None
    if not isinstance(units, int) or units < 0 or (mode == "add" and units == 0):
        return {"error": "units must be a positive whole number"}, None
    live = await shopify.catalog()
    variants = [v for v in await shopify_admin.variants_with_inventory() if v["handle"] in live]
    found = _match(product, variants)
    if not found:
        return {"error": f"No product on sale matches '{product}'.",
                "products_on_sale": [v["name"] for v in variants]}, None
    if len(found) > 1:
        return {"error": "Several variants match — ask the owner which one.",
                "candidates": [{"name": v["name"], "qty": v["qty"]} for v in found]}, None
    v = found[0]
    to_qty = v["qty"] + units if mode == "add" else units
    change = to_qty - v["qty"]
    if change == 0:
        return {"error": f"{v['name']} already has {v['qty']} units."}, None
    if abs(change) > MAX_UNITS or to_qty > MAX_STOCK or to_qty < 0:
        return {"error": f"Changes are limited to {MAX_UNITS} units at a time and {MAX_STOCK} in total; "
                         "bigger adjustments are done in Shopify admin."}, None
    _clean()
    for k in [k for k, p in _PENDING.items() if p.chat_id == chat_id]:  # one open proposal per chat
        del _PENDING[k]
    pid = secrets.token_hex(4)
    _PENDING[pid] = Proposal(chat_id, v["name"], v["handle"], v["item_id"], v["location_id"], v["qty"], to_qty, time.time())
    return {"proposal": {"product": v["name"], "current_units": v["qty"], "new_units": to_qty, "change": change},
            "status": "NOT applied yet: a Confirm / Cancel button is attached to your reply; the change happens "
                      "only if the owner taps Confirm."}, pid


async def _log(p: Proposal, status: str, final: int | None, error: str = "") -> None:
    await db.insert("stock_changes", {
        "chat_id": p.chat_id, "product": p.name, "inventory_item_id": p.item_id, "from_qty": p.from_qty,
        "to_qty": p.to_qty, "final_qty": final, "status": status, "error": error[:300] or None,
        "created_at": datetime.now(timezone.utc).isoformat()})


async def confirm(chat_id: str, pid: str) -> tuple[str, str]:
    """Apply a proposal. Returns (message text for Telegram, short toast)."""
    _clean()
    p = _PENDING.get(pid)
    if not p or p.chat_id != chat_id or chat_id != config.TELEGRAM_OWNER_CHAT_ID:
        return "⌛ This request expired or was replaced — ask again and I'll prepare a new one.", "Expired"
    del _PENDING[pid]  # one shot: a double tap can't apply it twice
    errors = await shopify_admin.set_available(p.item_id, p.location_id, p.to_qty, p.from_qty,
                                               ref=f"gid://ardea-owner-bot/Restock/{pid}")
    final = await shopify_admin.available_qty(p.item_id, p.location_id)
    if errors:
        await _log(p, "rejected", final, "; ".join(errors))
        log.info("restock rejected: %s", errors)
        return (f"⚠️ Nothing changed: the stock of <b>{notify.esc(p.name)}</b> moved since I prepared this "
                f"(now {final} units). Ask again and I'll use the current number.", "Not applied")
    await _log(p, "applied", final)
    web_cache.refresh_products_soon()
    back = " It's back on sale in the store." if p.from_qty <= 0 < (final or 0) else ""
    return f"✅ Done. <b>{notify.esc(p.name)}</b>: {p.from_qty} → <b>{final}</b> units.{back}", "Stock updated"


def cancel(chat_id: str, pid: str) -> str:
    p = _PENDING.get(pid)
    if p and p.chat_id == chat_id:
        del _PENDING[pid]
    return "Cancelled — nothing was changed."
