"""Scheduled owner reports: a daily summary (every day at DIGEST_HOUR, DIGEST_TZ) and a weekly report with
charts (Mondays). They replace one-message-per-event alerts, which stop being manageable at real traffic.

The scheduler is a small asyncio loop started with the app. Each job's last local run date is kept in
Supabase (bot_jobs), so restarts never send twice and a report missed during downtime goes out once.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from . import analytics, charts, config, db, notify, shopify, shopify_admin

log = logging.getLogger("reports")
TZ = ZoneInfo(config.DIGEST_TZ)
esc = notify.esc
_LAST_RUN_FALLBACK: dict[str, date] = {}  # used only if Supabase is unreachable


def _money(v: float) -> str:
    return f"${v:,.2f}"


def _delta(now: float, before: float) -> str:
    if before <= 0:
        return "" if now <= 0 else " · new"
    pct = (now - before) / before * 100
    return f" · {'▲' if pct >= 0 else '▼'} {abs(pct):.0f}%"


def _local_bounds(d: date) -> tuple[datetime, datetime]:
    start = datetime.combine(d, time(0), TZ)
    return start, start + timedelta(days=1)


async def _orders_on(days: list[date]) -> list[dict]:
    lo, _ = _local_bounds(min(days))
    _, hi = _local_bounds(max(days))
    return [o for o in await analytics.orders() if lo <= o["at"] < hi]


def _totals(rows: list[dict]) -> dict:
    revenue = sum(o["total"] for o in rows)
    return {"orders": len(rows), "revenue": revenue, "avg": revenue / len(rows) if rows else 0.0,
            "customers": len({o["customer_id"] for o in rows if o["customer_id"]})}


def _top_products(rows: list[dict], n: int) -> list[tuple[str, int]]:
    units: dict[str, int] = {}
    for o in rows:
        for li in o["lines"]:
            units[li["product"]] = units.get(li["product"], 0) + li["qty"]
    return sorted(units.items(), key=lambda kv: kv[1], reverse=True)[:n]


async def _stock_lines() -> list[str]:
    live = await shopify.catalog()
    rows = sorted((v for v in await shopify_admin.stock_levels() if v["handle"] in live), key=lambda v: v["qty"])
    return [f"⛔ {esc(v['name'])} — sold out" if v["qty"] <= 0 else f"📉 {esc(v['name'])} — {v['qty']} left"
            for v in rows if v["qty"] <= config.LOW_STOCK_AT]


async def daily_digest(today: date | None = None) -> str:
    today = today or datetime.now(TZ).date()
    y, before = today - timedelta(days=1), today - timedelta(days=2)
    rows_y, rows_b = await _orders_on([y]), await _orders_on([before])
    t, b = _totals(rows_y), _totals(rows_b)
    out = [f"🌅 <b>Daily summary · {y:%a %b} {y.day}</b>", ""]
    if t["orders"]:
        out.append(f"<b>{_money(t['revenue'])}</b> from {t['orders']} order{'s' * (t['orders'] != 1)}"
                   f"{_delta(t['revenue'], b['revenue'])} vs the day before")
        out.append(f"Average order {_money(t['avg'])} · {t['customers']} customer{'s' * (t['customers'] != 1)}")
        top = _top_products(rows_y, 1)
        if top:
            out.append(f"Star product: {esc(top[0][0])} ({top[0][1]} unit{'s' * (top[0][1] != 1)})")
    else:
        out.append("No orders yesterday.")

    stock = await _stock_lines()
    out += ["", "<b>Stock to watch</b>"] + (stock or ["✅ Everything above 10 units"])

    lo, hi = _local_bounds(y)
    convs = await db.select(f"conversations?select=id&created_at=gte.{lo.astimezone(timezone.utc).isoformat()}"
                            f"&created_at=lt.{hi.astimezone(timezone.utc).isoformat()}".replace("+00:00", "Z")) or []
    pending = await db.select("escalations?select=ref_code,kind,summary&status=eq.open&order=created_at") or []
    out += ["", f"<b>Store chat</b> · {len(convs)} conversation{'s' * (len(convs) != 1)} yesterday"]
    if pending:
        out.append(f"{len(pending)} case{'s' * (len(pending) != 1)} waiting for you:")
        out += [f"• <code>{esc(p['ref_code'])}</code> {esc(notify.LABELS.get(p['kind'], 'Case'))}: "
                f"{esc((p['summary'] or '')[:140])}" for p in pending[:8]]
        if len(pending) > 8:
            out.append(f"…and {len(pending) - 8} more")
    else:
        out.append("No cases waiting.")
    return "\n".join(out)


async def mark_pending_notified() -> None:
    await db.update("escalations?status=eq.open",
                    {"status": "notified", "notified_at": datetime.now(timezone.utc).isoformat()})


async def weekly_report(today: date | None = None) -> tuple[str, list[bytes]]:
    today = today or datetime.now(TZ).date()
    end = today - timedelta(days=1)                       # last full day (Sunday when sent on Monday)
    week = [end - timedelta(days=i) for i in range(7)]
    prev = [d - timedelta(days=7) for d in week]
    rows, rows_prev = await _orders_on(week), await _orders_on(prev)
    t, p = _totals(rows), _totals(rows_prev)
    start = week[-1]
    out = [f"📊 <b>Weekly report · {start:%b} {start.day} – {end:%b} {end.day}</b>", "",
           f"Revenue <b>{_money(t['revenue'])}</b>{_delta(t['revenue'], p['revenue'])} vs previous week",
           f"Orders {t['orders']}{_delta(t['orders'], p['orders'])} · average {_money(t['avg'])} · "
           f"{t['customers']} customer{'s' * (t['customers'] != 1)}"]
    top = _top_products(rows, 3)
    if top:
        out += ["", "<b>Top products</b>"] + [f"{i}. {esc(n)} — {u} units" for i, (n, u) in enumerate(top, 1)]

    photos: list[bytes] = []
    days28 = [end - timedelta(days=i) for i in range(27, -1, -1)]
    rows28 = await _orders_on(days28)
    daily = {d: 0.0 for d in days28}
    for o in rows28:
        daily[o["at"].astimezone(TZ).date()] = daily.get(o["at"].astimezone(TZ).date(), 0.0) + o["total"]
    photos.append(charts.time_line("Daily revenue", f"USD · last 4 weeks ({days28[0]:%b} {days28[0].day} – {end:%b} {end.day})",
                                   days28, [daily[d] for d in days28], fmt=lambda v: f"${v:,.0f}"))
    top10 = _top_products(rows, 10)
    if top10:
        photos.append(charts.ranked_bars("Best sellers this week", f"Units sold · {start:%b} {start.day} – {end:%b} {end.day}",
                                         [n for n, _ in top10], [u for _, u in top10]))
    return "\n".join(out), photos


# ── scheduler ────────────────────────────────────────────────────────────────────────────────────────

async def _last_run(job: str) -> date | None:
    rows = await db.select(f"bot_jobs?select=last_run&name=eq.{job}")
    if rows is None:
        return _LAST_RUN_FALLBACK.get(job)
    return date.fromisoformat(rows[0]["last_run"]) if rows else None


async def _set_run(job: str, d: date) -> None:
    _LAST_RUN_FALLBACK[job] = d
    await db.insert("bot_jobs", {"name": job, "last_run": d.isoformat(),
                                 "updated_at": datetime.now(timezone.utc).isoformat()}, upsert=True)


async def send_daily(chat_id: str | None = None) -> None:
    await notify.telegram(await daily_digest(), chat_id)
    if chat_id in (None, config.TELEGRAM_OWNER_CHAT_ID):
        await mark_pending_notified()


async def send_weekly(chat_id: str | None = None) -> None:
    chat_id = chat_id or config.TELEGRAM_OWNER_CHAT_ID
    text, photos = await weekly_report()
    await notify.telegram(text, chat_id)
    for png in photos:
        await notify.telegram_photo(png, chat_id)


async def tick(now: datetime | None = None) -> None:
    now = now or datetime.now(TZ)
    if now.hour < config.DIGEST_HOUR:
        return
    today = now.date()
    if await _last_run("daily_digest") != today:
        await _set_run("daily_digest", today)  # claim first: a slow send must not be repeated by the next tick
        await send_daily()
        log.info("daily digest sent")
    if now.weekday() == 0 and await _last_run("weekly_report") != today:
        await _set_run("weekly_report", today)
        await send_weekly()
        log.info("weekly report sent")


async def scheduler() -> None:
    while True:
        if notify.enabled():
            try:
                await tick()
            except Exception as e:  # noqa: BLE001 — never let the loop die
                log.warning("scheduled report failed: %s", e.__class__.__name__)
        await asyncio.sleep(60)
