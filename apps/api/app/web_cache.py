"""Tell the Next.js storefront to drop its cached product data (stock changes show up at once).

The storefront caches Shopify data for minutes; after a stock change the API calls the web container's
/api/revalidate route. The shared secret is derived from the Shopify client secret, which both containers
already read from the same .env, so there is nothing extra to configure. Fail-soft: if the call fails the
cache simply expires on its own a minute later.
"""
from __future__ import annotations

import hashlib
import logging

import httpx

from . import config

log = logging.getLogger("web_cache")


def secret() -> str:
    return hashlib.sha256(f"ardea-revalidate:{config.SHOPIFY_CLIENT_SECRET}".encode()).hexdigest()


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
