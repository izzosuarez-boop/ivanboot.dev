"""Supabase (PostgREST) persistence. Fail-soft: if the database is unreachable the chat keeps working,
the write is skipped and logged — the visitor never sees a database error."""
from __future__ import annotations

import logging

import httpx

from . import config

log = logging.getLogger("agent.db")


def enabled() -> bool:
    return bool(config.SUPABASE_URL and config.SUPABASE_SECRET_KEY)


def _headers(prefer: str = "return=minimal") -> dict:
    return {"apikey": config.SUPABASE_SECRET_KEY, "Authorization": f"Bearer {config.SUPABASE_SECRET_KEY}",
            "Content-Type": "application/json", "Prefer": prefer}


async def insert(table: str, row: dict | list, *, upsert: bool = False, returning: bool = False) -> list | None:
    if not enabled():
        return None
    prefer = ("resolution=merge-duplicates," if upsert else "") + ("return=representation" if returning else "return=minimal")
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            r = await http.post(f"{config.SUPABASE_URL}/rest/v1/{table}", json=row, headers=_headers(prefer))
        if r.status_code >= 300:
            log.warning("supabase insert %s -> %s %s", table, r.status_code, r.text[:200])
            return None
        return r.json() if returning else []
    except httpx.HTTPError as e:
        log.warning("supabase insert %s failed: %s", table, e)
        return None


async def select(path: str) -> list | None:
    if not enabled():
        return None
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            r = await http.get(f"{config.SUPABASE_URL}/rest/v1/{path}", headers=_headers())
        return r.json() if r.status_code < 300 else None
    except httpx.HTTPError:
        return None


async def rpc(fn: str, args: dict | None = None):
    if not enabled():
        return None
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            r = await http.post(f"{config.SUPABASE_URL}/rest/v1/rpc/{fn}", json=args or {}, headers=_headers())
        return r.json() if r.status_code < 300 else None
    except httpx.HTTPError:
        return None
