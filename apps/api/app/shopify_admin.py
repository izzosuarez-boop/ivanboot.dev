"""Shopify Admin GraphQL (async) for the owner bot: order lookups and stock levels.

Auth is the client credentials grant of the Dev Dashboard app (token valid 24 h, cached in memory).
Only order numbers, totals and line items are read — never customer names, emails or addresses.
"""
from __future__ import annotations

import time

import httpx

from . import config

_TOKEN: str | None = None
_TOKEN_EXP = 0.0


def enabled() -> bool:
    return bool(config.SHOPIFY_SHOP and config.SHOPIFY_CLIENT_ID and config.SHOPIFY_CLIENT_SECRET)


async def _token(http: httpx.AsyncClient) -> str:
    global _TOKEN, _TOKEN_EXP
    if _TOKEN and time.time() < _TOKEN_EXP - 60:
        return _TOKEN
    r = await http.post(f"https://{config.SHOPIFY_SHOP}.myshopify.com/admin/oauth/access_token",
                        data={"grant_type": "client_credentials", "client_id": config.SHOPIFY_CLIENT_ID,
                              "client_secret": config.SHOPIFY_CLIENT_SECRET})
    r.raise_for_status()
    data = r.json()
    _TOKEN, _TOKEN_EXP = data["access_token"], time.time() + int(data.get("expires_in", 86399))
    return _TOKEN


async def gql(query: str, variables: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=15) as http:
        token = await _token(http)
        r = await http.post(
            f"https://{config.SHOPIFY_SHOP}.myshopify.com/admin/api/{config.SHOPIFY_API_VERSION}/graphql.json",
            json={"query": query, "variables": variables or {}}, headers={"X-Shopify-Access-Token": token})
    r.raise_for_status()
    data = r.json()
    if data.get("errors"):
        raise RuntimeError(str(data["errors"])[:300])
    return data["data"]


async def inventory_item(item_id: int | str) -> dict | None:
    """Variant name + product handle for an inventory item id (from the inventory_levels webhook)."""
    data = await gql("""query($id: ID!) { inventoryItem(id: $id) {
        variant { displayName inventoryQuantity product { handle title } } } }""",
                     {"id": f"gid://shopify/InventoryItem/{item_id}"})
    v = (data.get("inventoryItem") or {}).get("variant")
    if not v:
        return None
    return {"name": v["displayName"], "handle": v["product"]["handle"], "total": v["inventoryQuantity"]}


async def stock_levels() -> list[dict]:
    """Every variant with its total stock: [{name, handle, qty}]."""
    data = await gql("""{ productVariants(first: 100) { nodes {
        displayName inventoryQuantity product { handle } } } }""")
    return [{"name": n["displayName"], "handle": n["product"]["handle"], "qty": n["inventoryQuantity"]}
            for n in data["productVariants"]["nodes"]]


async def recent_orders(n: int = 5) -> list[dict]:
    data = await gql("""query($n: Int!) { orders(first: $n, sortKey: CREATED_AT, reverse: true) { nodes {
        name createdAt test displayFinancialStatus
        totalPriceSet { shopMoney { amount currencyCode } }
        lineItems(first: 10) { nodes { name quantity } } } } }""", {"n": n})
    return [{"name": o["name"], "created": o["createdAt"], "test": o["test"],
             "status": o["displayFinancialStatus"],
             "total": f'{o["totalPriceSet"]["shopMoney"]["amount"]} {o["totalPriceSet"]["shopMoney"]["currencyCode"]}',
             "items": [f'{li["quantity"]}× {li["name"]}' for li in o["lineItems"]["nodes"]]}
            for o in data["orders"]["nodes"]]
