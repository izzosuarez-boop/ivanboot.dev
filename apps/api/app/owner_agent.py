"""Back-office assistant for the store owner, inside Telegram (Claude Haiku 5.5 + tools).

The owner writes in plain language ("best sellers of the last 3 months as a chart", "top 10 buyers"); the
model picks the tool, the numbers come only from Shopify via analytics.py, and charts are rendered server-side
(charts.py) and sent as photos. The model never draws or invents data: a tool's `chart` flag asks the server
to render exactly the data it returned.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from . import analytics, charts, config, db, guard, shopify, shopify_admin
from .agent import client, cost_of

MAX_TURNS_KEPT = 12  # remembered text turns per chat (tool calls are not kept between questions)
TTL = 2 * 3600

SYSTEM = """You are the back-office assistant of Ardea Skin (a demo skincare store on Shopify), talking to the
store owner inside Telegram. Today is {today} (UTC).

- Answer in the owner's language (Spanish or English), short and direct: a one-line headline, then at most a
  few bullet lines ("• "). Money in USD with 2 decimals at most.
- Numbers come ONLY from your tools. Never estimate, extrapolate or invent figures, names or products. If a
  tool can't answer, say what you can show instead.
- Charts: when the owner asks for a chart/graph/gráfica/visual, call the tool with chart=true — the image is
  sent automatically right after your text, so don't mention or announce it and don't describe pixels;
  summarise the 2-3 key facts instead.
  Rankings → bar chart; evolution over time → line chart (get_sales).
- Periods: "last 3 months" = 90 days, "this month" = days since the 1st, "last week" = 7, "this year" = days
  since Jan 1 (max 365). Mention the period you used.
- Telegram formatting: plain text plus <b>bold</b> and <i>italic</i> only. No markdown, no tables, no headings.
- The sales history is demo data generated for this portfolio project; say so only if asked.
- Customer names are private store data: fine to show to the owner here, never suggest sharing them.
- Earlier answers in this chat end with an [answered from: …] note: those numbers came from tools and any
  chart was already sent. Don't re-check or re-send them; call a tool only for what the new message needs.
  Never write such a note yourself.
- You can only read data. If asked to change prices, stock or orders, explain that it is done in Shopify admin."""

DAYS = {"type": "integer", "minimum": 1, "maximum": 365, "description": "Window in days ending today"}
CHART = {"type": "boolean", "description": "Render and send a chart image of this result"}
TOOLS = [
    {"name": "get_sales", "description": "Revenue, orders, units, average order and customers for a period, plus a "
     "time series grouped by day, week or month (line chart).",
     "input_schema": {"type": "object", "properties": {"days": DAYS, "group_by": {"type": "string", "enum": ["day", "week", "month"]},
                                                       "chart": CHART}, "required": ["days"]}},
    {"name": "get_top_products", "description": "Best-selling products in a period, ranked by units or revenue (bar chart).",
     "input_schema": {"type": "object", "properties": {"days": DAYS, "n": {"type": "integer", "minimum": 1, "maximum": 20},
                                                       "metric": {"type": "string", "enum": ["units", "revenue"]},
                                                       "chart": CHART}, "required": ["days"]}},
    {"name": "get_top_customers", "description": "Customers who spent the most in a period, with order count (bar chart).",
     "input_schema": {"type": "object", "properties": {"days": DAYS, "n": {"type": "integer", "minimum": 1, "maximum": 20},
                                                       "chart": CHART}, "required": ["days"]}},
    {"name": "get_stock", "description": "Current stock of every variant on sale (low = 5 or fewer).",
     "input_schema": {"type": "object", "properties": {"only_low": {"type": "boolean"}}}},
    {"name": "get_recent_orders", "description": "The latest orders with totals and items.",
     "input_schema": {"type": "object", "properties": {"n": {"type": "integer", "minimum": 1, "maximum": 10}}}},
    {"name": "get_chat_stats", "description": "Usage and AI spend of the store's customer chat.",
     "input_schema": {"type": "object", "properties": {}}},
]


@dataclass
class OwnerChat:
    messages: list = field(default_factory=list)
    touched: float = field(default_factory=time.time)


_CHATS: dict[str, OwnerChat] = {}


def reset(chat_id: str) -> None:
    _CHATS.pop(chat_id, None)


def _chat(chat_id: str) -> OwnerChat:
    now = time.time()
    for k in [k for k, c in _CHATS.items() if now - c.touched > TTL]:
        del _CHATS[k]
    c = _CHATS.setdefault(chat_id, OwnerChat())
    c.touched = now
    return c


def _money(v: float) -> str:
    return f"${v:,.0f}" if v >= 100 else f"${v:,.2f}"


async def _run_tool(name: str, a: dict, photos: list[tuple[bytes, str]]) -> dict:
    if name == "get_sales":
        r = await analytics.sales(a.get("days", 30), a.get("group_by") or ("month" if a.get("days", 30) > 120 else "week"))
        if a.get("chart") and r["series"]:
            label = {"day": "Daily", "week": "Weekly", "month": "Monthly"}[r["group_by"]]
            photos.append((charts.time_line(f"{label} revenue", f"USD · {r['period']} · {r['orders']} orders",
                                            [date.fromisoformat(s["start"]) for s in r["series"]],
                                            [s["revenue_usd"] for s in r["series"]], fmt=_money), "sales"))
        if len(r["series"]) > 16:  # keep the model's context small; the chart has the full series
            r["series"] = r["series"][-16:]
            r["series_note"] = "only the last 16 buckets are listed"
        return r
    if name == "get_top_products":
        r = await analytics.top_products(a.get("days", 90), a.get("n", 10), a.get("metric", "units"))
        if a.get("chart") and r["products"]:
            rev = r["metric"] == "revenue_usd"
            photos.append((charts.ranked_bars("Best sellers", f"{'Revenue' if rev else 'Units sold'} · {r['period']}",
                                              [p["product"] for p in r["products"]],
                                              [p[r["metric"]] for p in r["products"]],
                                              fmt=_money if rev else (lambda v: f"{v:,.0f}")), "products"))
        return r
    if name == "get_top_customers":
        r = await analytics.top_customers(a.get("days", 90), a.get("n", 10))
        if a.get("chart") and r["customers"]:
            photos.append((charts.ranked_bars(f"Top {len(r['customers'])} customers", f"Total spent · {r['period']}",
                                              [c["customer"] for c in r["customers"]],
                                              [c["spent_usd"] for c in r["customers"]], fmt=_money), "customers"))
        return r
    if name == "get_stock":
        live = await shopify.catalog()
        rows = sorted((v for v in await shopify_admin.stock_levels() if v["handle"] in live), key=lambda v: v["qty"])
        if a.get("only_low"):
            rows = [v for v in rows if v["qty"] <= config.LOW_STOCK_AT]
        return {"low_stock_at": config.LOW_STOCK_AT, "variants": [{"name": v["name"], "qty": v["qty"]} for v in rows]}
    if name == "get_recent_orders":
        return {"orders": await shopify_admin.recent_orders(a.get("n", 5))}
    if name == "get_chat_stats":
        return {"all_time": await db.rpc("agent_stats") or {}, "spend_today_usd": round(await guard.spent_today(), 4),
                "daily_cap_usd": config.DAILY_BUDGET_USD}
    return {"error": f"unknown tool {name}"}


async def ask(chat_id: str, text: str) -> tuple[str, list[tuple[bytes, str]], float]:
    """Returns (reply text in Telegram HTML, chart PNGs, cost in USD)."""
    chat = _chat(chat_id)
    turn = chat.messages + [{"role": "user", "content": text[:1500]}]
    photos: list[tuple[bytes, str]] = []
    used: list[str] = []
    cost, reply = 0.0, ""
    system = SYSTEM.format(today=datetime.now(timezone.utc).date().isoformat())
    for _ in range(5):
        resp = await client.messages.create(
            model=config.AGENT_MODEL, max_tokens=1200, system=system, tools=TOOLS, messages=turn,
            thinking={"type": "adaptive"}, output_config={"effort": "low"})
        cost += cost_of(resp.usage)
        turn.append({"role": "assistant", "content": [b.model_dump(exclude_none=True) for b in resp.content]})
        if resp.stop_reason != "tool_use":
            reply = "".join(b.text for b in resp.content if b.type == "text").strip()
            break
        results = []
        for b in resp.content:
            if b.type == "tool_use":
                used.append(f"{b.name}({json.dumps(b.input or {}, separators=(',', ':'))})")
                try:
                    out = await _run_tool(b.name, b.input or {}, photos)
                except Exception as e:  # noqa: BLE001 — report to the model, it explains to the owner
                    out = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(out, default=str)})
        turn.append({"role": "user", "content": results})
    guard.add_spend(cost)
    reply = reply or "I couldn't finish that one — could you rephrase it?"
    # remember the text of each exchange plus which tools fed it: small context, follow-ups ("now by revenue")
    # still work, and the model knows earlier numbers were real tool data (so it doesn't re-fetch or re-send)
    note = f"\n\n[answered from: {'; '.join(used)}{'; chart sent' if photos else ''}]" if used else ""
    chat.messages = (chat.messages + [{"role": "user", "content": text[:1500]},
                                      {"role": "assistant", "content": reply + note}])[-MAX_TURNS_KEPT:]
    return reply, photos, cost
