"""Sales analytics for the owner bot, computed from Shopify orders (the source of truth).

Orders of the last year are fetched once through the Admin API and cached for a few minutes; every question
(sales over time, best sellers, best customers) is an in-memory aggregation over that snapshot.
Cancelled orders are excluded. Customer names need Shopify's protected customer data (Name field);
without it customers are shown by a short id.
"""
from __future__ import annotations

import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from . import shopify_admin

CACHE_TTL = 300
MAX_DAYS = 365
_ORDERS: list[dict] | None = None
_ORDERS_AT = 0.0

ORDERS_Q = """query($cursor: String, $q: String!) {
  orders(first: 50, after: $cursor, query: $q, sortKey: PROCESSED_AT) {
    pageInfo { hasNextPage endCursor }
    nodes { name processedAt cancelledAt test
      totalPriceSet { shopMoney { amount } }
      customer { id %s }
      lineItems(first: 10) { nodes { quantity product { handle title }
        discountedTotalSet { shopMoney { amount } } } } } } }"""


async def _fetch(with_names: bool) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=MAX_DAYS)).date().isoformat()
    query, cursor, out = ORDERS_Q % ("displayName" if with_names else ""), None, []
    while True:
        data = (await shopify_admin.gql(query, {"cursor": cursor, "q": f"processed_at:>={since} status:any"}))["orders"]
        for o in data["nodes"]:
            if o["cancelledAt"]:
                continue
            c = o.get("customer") or {}
            cid = (c.get("id") or "").rsplit("/", 1)[-1]
            out.append({
                "name": o["name"], "day": datetime.fromisoformat(o["processedAt"].replace("Z", "+00:00")).date(),
                "total": float(o["totalPriceSet"]["shopMoney"]["amount"]),
                "customer_id": cid or None,
                "customer": c.get("displayName") or (f"Customer …{cid[-4:]}" if cid else "Guest"),
                "lines": [{"product": (li.get("product") or {}).get("title") or "Unknown product",
                           "qty": li["quantity"], "revenue": float(li["discountedTotalSet"]["shopMoney"]["amount"])}
                          for li in o["lineItems"]["nodes"]],
            })
        if not data["pageInfo"]["hasNextPage"]:
            return out
        cursor = data["pageInfo"]["endCursor"]


async def orders() -> list[dict]:
    global _ORDERS, _ORDERS_AT
    if _ORDERS is not None and time.time() - _ORDERS_AT < CACHE_TTL:
        return _ORDERS
    try:
        _ORDERS = await _fetch(with_names=True)
    except RuntimeError as e:  # protected customer data (Name) not granted yet
        if "ACCESS_DENIED" not in str(e) and "not approved" not in str(e):
            raise
        _ORDERS = await _fetch(with_names=False)
    _ORDERS_AT = time.time()
    return _ORDERS


def _window(days: int) -> tuple[date, date]:
    days = max(1, min(int(days), MAX_DAYS))
    today = datetime.now(timezone.utc).date()
    return today - timedelta(days=days - 1), today


def period_label(days: int) -> str:
    start, end = _window(days)
    return f"{start:%b} {start.day} – {end:%b} {end.day}"


async def _in(days: int) -> list[dict]:
    start, end = _window(days)
    return [o for o in await orders() if start <= o["day"] <= end]


def _bucket(d: date, group: str) -> date:
    if group == "month":
        return d.replace(day=1)
    if group == "week":
        return d - timedelta(days=d.weekday())
    return d


async def sales(days: int = 30, group: str = "week") -> dict:
    rows = await _in(days)
    start, end = _window(days)
    series: dict[date, float] = defaultdict(float)
    counts: dict[date, int] = defaultdict(int)
    d = _bucket(start, group)
    while d <= end:  # include empty buckets so the line doesn't skip gaps
        series[d], counts[d] = 0.0, 0
        d = (d + timedelta(days=32)).replace(day=1) if group == "month" else d + timedelta(days=7 if group == "week" else 1)
    for o in rows:
        b = _bucket(o["day"], group)
        series[b] += o["total"]
        counts[b] += 1
    revenue = sum(o["total"] for o in rows)
    return {"period": period_label(days), "days": days, "orders": len(rows), "revenue_usd": round(revenue, 2),
            "avg_order_usd": round(revenue / len(rows), 2) if rows else 0,
            "units": sum(li["qty"] for o in rows for li in o["lines"]),
            "customers": len({o["customer_id"] for o in rows if o["customer_id"]}),
            "group_by": group,
            "series": [{"start": k.isoformat(), "revenue_usd": round(series[k], 2), "orders": counts[k]}
                       for k in sorted(series)]}


async def top_products(days: int = 90, n: int = 10, metric: str = "units") -> dict:
    agg: dict[str, dict] = defaultdict(lambda: {"units": 0, "revenue_usd": 0.0, "orders": 0})
    for o in await _in(days):
        for p in {li["product"] for li in o["lines"]}:
            agg[p]["orders"] += 1
        for li in o["lines"]:
            agg[li["product"]]["units"] += li["qty"]
            agg[li["product"]]["revenue_usd"] += li["revenue"]
    key = "revenue_usd" if metric == "revenue" else "units"
    ranked = sorted(agg.items(), key=lambda kv: kv[1][key], reverse=True)[:max(1, min(n, 20))]
    return {"period": period_label(days), "days": days, "metric": key,
            "products": [{"product": k, "units": v["units"], "revenue_usd": round(v["revenue_usd"], 2),
                          "orders": v["orders"]} for k, v in ranked]}


async def top_customers(days: int = 90, n: int = 10) -> dict:
    agg: dict[str, dict] = {}
    for o in await _in(days):
        if not o["customer_id"]:
            continue
        a = agg.setdefault(o["customer_id"], {"customer": o["customer"], "orders": 0, "spent_usd": 0.0, "last": o["day"]})
        a["orders"] += 1
        a["spent_usd"] += o["total"]
        a["last"] = max(a["last"], o["day"])
    ranked = sorted(agg.values(), key=lambda a: a["spent_usd"], reverse=True)[:max(1, min(n, 20))]
    return {"period": period_label(days), "days": days,
            "customers": [{"customer": a["customer"], "orders": a["orders"], "spent_usd": round(a["spent_usd"], 2),
                           "last_order": a["last"].isoformat()} for a in ranked]}
