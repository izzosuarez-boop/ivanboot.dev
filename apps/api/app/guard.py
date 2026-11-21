"""Abuse and budget protection for a public chat: per-visitor rate limits and a daily spend cap."""
from __future__ import annotations

import datetime as dt
import hashlib
import time
from collections import defaultdict, deque

from . import config, db

_hits: dict[str, deque] = defaultdict(deque)
_spend = {"day": "", "usd": 0.0, "seeded": False}


def visitor_hash(ip: str, user_agent: str) -> str:
    return hashlib.sha256(f"{config.HASH_SALT}|{ip}|{user_agent[:120]}".encode()).hexdigest()[:24]


def rate_limited(visitor: str) -> str | None:
    """Returns a reason string when the visitor should wait, else None."""
    now = time.time()
    q = _hits[visitor]
    while q and now - q[0] > 3600:
        q.popleft()
    last_minute = sum(1 for t in q if now - t < 60)
    if last_minute >= config.RATE_PER_MINUTE:
        return "minute"
    if len(q) >= config.RATE_PER_HOUR:
        return "hour"
    q.append(now)
    if len(_hits) > 5000:  # keep memory bounded
        for k in list(_hits)[:1000]:
            _hits.pop(k, None)
    return None


def _today() -> str:
    return dt.datetime.now(dt.timezone.utc).date().isoformat()


async def spent_today() -> float:
    today = _today()
    if _spend["day"] != today:
        _spend.update(day=today, usd=0.0, seeded=False)
    if not _spend["seeded"]:  # after a restart, pick up what was already spent today
        rows = await db.select(f"messages?select=cost_usd&created_at=gte.{today}T00:00:00Z")
        if rows is not None:
            _spend["usd"] = max(_spend["usd"], sum(float(r.get("cost_usd") or 0) for r in rows))
            _spend["seeded"] = True
    return _spend["usd"]


def add_spend(usd: float) -> None:
    if _spend["day"] != _today():
        _spend.update(day=_today(), usd=0.0, seeded=False)
    _spend["usd"] += usd


async def over_budget() -> bool:
    return await spent_today() >= config.DAILY_BUDGET_USD
