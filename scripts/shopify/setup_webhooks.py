"""Subscribe the store to the webhooks the owner bot needs (idempotent).

    python scripts/shopify/setup_webhooks.py          # create missing subscriptions, list all
    python scripts/shopify/setup_webhooks.py --test   # also send a signed fake inventory event to the API

Shopify signs every delivery with the app's client secret (X-Shopify-Hmac-Sha256); the API verifies it.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sys
import urllib.request

from shopify_admin import ShopifyAdmin, load_env, raise_user_errors

sys.stdout.reconfigure(encoding="utf-8")
URI = "https://api.ivanboot.dev/webhooks/shopify"
TOPICS = ["ORDERS_CREATE", "INVENTORY_LEVELS_UPDATE"]


def main() -> int:
    s = ShopifyAdmin()
    existing = s.gql("{ webhookSubscriptions(first: 50) { nodes { id topic uri } } }")["webhookSubscriptions"]["nodes"]
    have = {(w["topic"], w["uri"]) for w in existing}
    for topic in TOPICS:
        if (topic, URI) in have:
            print(f"  ok       {topic}")
            continue
        res = s.gql("""mutation($topic: WebhookSubscriptionTopic!, $sub: WebhookSubscriptionInput!) {
            webhookSubscriptionCreate(topic: $topic, webhookSubscription: $sub) {
              webhookSubscription { id topic uri } userErrors { field message } } }""",
                    {"topic": topic, "sub": {"uri": URI, "format": "JSON"}})["webhookSubscriptionCreate"]
        raise_user_errors(res, f"webhookSubscriptionCreate {topic}")
        print(f"  created  {topic} -> {URI}")

    if "--test" in sys.argv:  # signed fake event: proves the API accepts Shopify's signature
        body = json.dumps({"inventory_item_id": 0, "available": 99}).encode()
        sig = base64.b64encode(hmac.new(load_env()["SHOPIFY_CLIENT_SECRET"].encode(), body, hashlib.sha256).digest()).decode()
        req = urllib.request.Request(URI, data=body, method="POST", headers={
            "Content-Type": "application/json", "X-Shopify-Topic": "inventory_levels/update",
            "X-Shopify-Hmac-Sha256": sig, "X-Shopify-Webhook-Id": "setup-test"})
        with urllib.request.urlopen(req, timeout=15) as r:
            print("  signed test delivery ->", r.status, r.read().decode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
