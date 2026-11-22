"""Tell the Next.js storefront to drop its cached product data (stock changes show up at once).

The storefront caches Shopify data for minutes; after a stock change the API calls the web container's
/api/revalidate route. The shared secret is derived from the Shopify client secret, which both containers
already read from the same .env, so there is nothing extra to configure. Fail-soft: if the call fails the
cache simply expires on its own a minute later.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging

import httpx

from . import config

log = logging.getLogger("web_cache")


def secret() -> str:
    return hashlib.sha256(f"ardea-revalidate:{config.SHOPIFY_CLIENT_SECRET}".encode()).hexdigest()


# Shopify's Storefront API is eventually consistent: for ~15-20 s after a stock change it answers from replicas
# that disagree (measured 2026-11-22: available / sold out alternating for 20 s). A single refresh right after
# the webhook can re-cache the OLD stock for another minute, so refresh again once the replicas have settled.
FOLLOW_UPS = (10, 25, 45, 90)  # seconds after the change (a sold-out once needed 40 s to settle)
_pending: set[asyncio.Task] = set()


def refresh_products_soon() -> None:
    """Refresh now and again after FOLLOW_UPS (fire and forget; safe to call from a webhook task)."""
    async def run() -> None:
        await refresh_products()
        waited = 0
        for at in FOLLOW_UPS:
            await asyncio.sleep(at - waited)
            waited = at
            await refresh_products()
    task = asyncio.create_task(run())
    _pending.add(task)  # keep a reference so the task isn't garbage-collected mid-way
    task.add_done_callback(_pending.discard)


async def refresh_products() -> bool:
    if not config.SHOPIFY_CLIENT_SECRET:
        return False
    try:
        async with httpx.AsyncClient(timeout=5) as http:
            r = await http.post(f"{config.WEB_INTERNAL_URL}/api/revalidate", json={"tags": ["products"]},
                                headers={"x-revalidate-secret": secret()})
        if r.status_code != 200:
            log.warning("storefront revalidate -> %s", r.status_code)
        return r.status_code == 200
    except httpx.HTTPError as e:
        log.warning("storefront revalidate failed: %s", e.__class__.__name__)
        return False
