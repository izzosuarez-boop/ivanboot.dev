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


# ── inventory writes (owner bot restock, always after the owner confirms) ─────────────────────────────

async def variants_with_inventory() -> list[dict]:
    """Every variant with what a stock change needs: [{name, handle, qty, item_id, location_id}].
    The store has a single location; a variant without an inventory level there can't be restocked."""
    data = await gql("""{ productVariants(first: 100) { nodes { displayName inventoryQuantity product { handle }
        inventoryItem { id tracked inventoryLevels(first: 1) { nodes { location { id }
          quantities(names: ["available"]) { quantity } } } } } } }""")
    out = []
    for n in data["productVariants"]["nodes"]:
        levels = n["inventoryItem"]["inventoryLevels"]["nodes"]
        if not n["inventoryItem"]["tracked"] or not levels:
            continue
        out.append({"name": n["displayName"], "handle": n["product"]["handle"],
                    "qty": levels[0]["quantities"][0]["quantity"],
                    "item_id": n["inventoryItem"]["id"], "location_id": levels[0]["location"]["id"]})
    return out


async def available_qty(item_id: str, location_id: str) -> int | None:
    data = await gql("""query($i: ID!, $l: ID!) { inventoryItem(id: $i) { inventoryLevel(locationId: $l) {
        quantities(names: ["available"]) { quantity } } } }""", {"i": item_id, "l": location_id})
    level = (data.get("inventoryItem") or {}).get("inventoryLevel")
    return level["quantities"][0]["quantity"] if level else None


async def set_available(item_id: str, location_id: str, quantity: int, expected: int, ref: str) -> list[str]:
    """Set the available quantity with a compare-and-swap: Shopify rejects the change if the stock is no
    longer `expected` (an order came in between proposal and confirmation). Returns user errors ([] = ok).
    `ref` doubles as the idempotency key Shopify requires, so a repeated request is applied only once."""
    data = await gql("""mutation($input: InventorySetQuantitiesInput!, $key: String!) {
        inventorySetQuantities(input: $input) @idempotent(key: $key) {
        userErrors { field message code } } }""", {"key": ref, "input": {
        "name": "available", "reason": "received", "referenceDocumentUri": ref,
        "quantities": [{"inventoryItemId": item_id, "locationId": location_id,
                        "quantity": quantity, "changeFromQuantity": expected}]}})
    return [e["message"] for e in data["inventorySetQuantities"]["userErrors"]]
