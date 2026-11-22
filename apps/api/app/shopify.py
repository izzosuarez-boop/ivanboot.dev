"""Shopify Storefront API (server-side, private token): catalog snapshot + live stock."""
from __future__ import annotations

import json
import re
import time

import httpx

from . import config

_CATALOG: dict | None = None
_CATALOG_AT = 0.0
CATALOG_TTL = 3600  # the snapshot goes into the cached system prompt, so keep it stable for an hour

FIELDS = """
  handle title productType
  variants(first: 10) { nodes { id title availableForSale quantityAvailable
    price { amount currencyCode } compareAtPrice { amount } } }
  metafields(identifiers: [
    {namespace: "ardea", key: "skin_types"}, {namespace: "ardea", key: "concerns"},
    {namespace: "ardea", key: "key_ingredients"}, {namespace: "ardea", key: "how_to_use"},
    {namespace: "ardea", key: "cautions"}, {namespace: "ardea", key: "routine_step"},
    {namespace: "ardea", key: "usage_time"}, {namespace: "ardea", key: "texture"},
    {namespace: "ardea", key: "fragrance_free"}]) { key value }
  description
"""


async def storefront(query: str, variables: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.post(
            f"https://{config.SHOPIFY_SHOP}.myshopify.com/api/{config.SHOPIFY_API_VERSION}/graphql.json",
            json={"query": query, "variables": variables or {}},
            headers={"Shopify-Storefront-Private-Token": config.SHOPIFY_STOREFRONT_PRIVATE_TOKEN},
        )
    r.raise_for_status()
    data = r.json()
    if data.get("errors"):
        raise RuntimeError(data["errors"])
    return data["data"]


def _meta(node: dict) -> dict:
    out = {}
    for m in node.get("metafields") or []:
        if not m:
            continue
        v = m["value"]
        try:
            v = json.loads(v) if v.startswith("[") else v
        except ValueError:
            pass
        out[m["key"]] = v
    return out


async def catalog() -> dict:
    """{handle: product} with static facts (no stock — stock is always fetched live)."""
    global _CATALOG, _CATALOG_AT
    if _CATALOG and time.time() - _CATALOG_AT < CATALOG_TTL:
        return _CATALOG
    data = await storefront(f"{{ products(first: 50, sortKey: TITLE) {{ nodes {{ {FIELDS} }} }} }}")
    cat = {}
    for p in data["products"]["nodes"]:
        m = _meta(p)
        cat[p["handle"]] = {
            "handle": p["handle"], "title": p["title"], "type": p["productType"],
            "routine_step": int(m.get("routine_step") or 0), "when": m.get("usage_time"),
            "texture": m.get("texture"), "fragrance_free": m.get("fragrance_free") == "true",
            "skin_types": m.get("skin_types") or [], "concerns": m.get("concerns") or [],
            "key_ingredients": m.get("key_ingredients") or [], "how_to_use": m.get("how_to_use"),
            "cautions": m.get("cautions"), "summary": p["description"][:400],
            "sizes": [{"size": v["title"], "price": v["price"]["amount"], "variant_id": v["id"]} for v in p["variants"]["nodes"]],
        }
    _CATALOG, _CATALOG_AT = cat, time.time()
    return cat


def catalog_for_prompt(cat: dict) -> str:
    """Compact, stable JSON for the system prompt (variant ids stay server-side)."""
    items = []
    for p in sorted(cat.values(), key=lambda x: (x["routine_step"], x["title"])):
        items.append({k: v for k, v in p.items() if k != "sizes"} | {
            "sizes": [{"size": s["size"], "price_usd": s["price"]} for s in p["sizes"]],
            "url": f"{config.STORE_URL}/products/{p['handle']}",
        })
    return json.dumps(items, ensure_ascii=False, separators=(",", ":"))


async def live_stock(handles: list[str]) -> list[dict]:
    """Live stock for exactly these products. (Until 2026-11-22 this used products(query: "handle:a OR …"),
    but the Storefront search ignores that filter and returned the whole catalog every time.)"""
    hs = [h for h in dict.fromkeys(handles) if re.fullmatch(r"[a-z0-9-]+", h)][:10]
    if not hs:
        return []
    fields = """handle title featuredImage { url }
             variants(first: 10) { nodes { id title availableForSale quantityAvailable
               price { amount } compareAtPrice { amount } } }"""
    data = await storefront("{ " + " ".join(f'p{i}: product(handle: "{h}") {{ {fields} }}' for i, h in enumerate(hs)) + " }")
    nodes = [data[f"p{i}"] for i in range(len(hs)) if data.get(f"p{i}")]
    out = []
    for p in nodes:
        out.append({
            "handle": p["handle"], "title": p["title"], "image": (p.get("featuredImage") or {}).get("url"),
            "sizes": [{
                "size": v["title"], "variant_id": v["id"], "price_usd": v["price"]["amount"],
                "on_sale_from": (v.get("compareAtPrice") or {}).get("amount"),
                "available": v["availableForSale"], "units_left": v["quantityAvailable"],
            } for v in p["variants"]["nodes"]],
        })
    return out
