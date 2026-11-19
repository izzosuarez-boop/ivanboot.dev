"""Minimal Shopify Admin GraphQL client (stdlib only).

Auth: client credentials grant (Dev Dashboard app installed on a store of the same
organization). Tokens last 24 h (expires_in=86399); we cache in memory and refresh
60 s before expiry. Credentials come from ../../.env or real environment variables
(real env wins).
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def load_env(path: Path = ENV_PATH) -> dict[str, str]:
    vals: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.lstrip().startswith("#"):
                continue
            m = re.match(r"\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$", line)
            if m:
                vals[m.group(1)] = m.group(2)
    vals.update({k: v for k, v in os.environ.items() if k.startswith("SHOPIFY_")})
    return vals


class ShopifyError(RuntimeError):
    pass


class ShopifyAdmin:
    def __init__(self, env: dict[str, str] | None = None):
        env = env or load_env()
        missing = [k for k in ("SHOPIFY_SHOP", "SHOPIFY_CLIENT_ID", "SHOPIFY_CLIENT_SECRET") if not env.get(k)]
        if missing:
            raise ShopifyError(f"Missing in .env: {', '.join(missing)}")
        self.shop = env["SHOPIFY_SHOP"]
        self.version = env.get("SHOPIFY_API_VERSION") or "2026-10"
        self._client_id = env["SHOPIFY_CLIENT_ID"]
        self._client_secret = env["SHOPIFY_CLIENT_SECRET"]
        self._token: str | None = None
        self._token_expires_at = 0.0
        self.granted_scopes: set[str] = set()

    # -- auth -----------------------------------------------------------------
    def _access_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token
        body = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }).encode()
        req = urllib.request.Request(
            f"https://{self.shop}.myshopify.com/admin/oauth/access_token",
            data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise ShopifyError(f"Token request failed: HTTP {e.code} {e.read().decode()[:200]}") from None
        self._token = data["access_token"]
        self._token_expires_at = time.time() + int(data.get("expires_in", 86399))
        self.granted_scopes = set(filter(None, data.get("scope", "").split(",")))
        return self._token

    def has_scope(self, scope: str) -> bool:
        """write_x implies read_x in Shopify's granted list."""
        self._access_token()
        if scope in self.granted_scopes:
            return True
        return scope.startswith("read_") and ("write_" + scope[5:]) in self.granted_scopes

    # -- graphql --------------------------------------------------------------
    def gql(self, query: str, variables: dict | None = None, *, retries: int = 4) -> dict:
        url = f"https://{self.shop}.myshopify.com/admin/api/{self.version}/graphql.json"
        payload = json.dumps({"query": query, "variables": variables or {}}).encode()
        for attempt in range(retries + 1):
            req = urllib.request.Request(url, data=payload, method="POST", headers={
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": self._access_token(),
            })
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    res = json.loads(r.read())
            except urllib.error.HTTPError as e:
                if e.code in (429, 502, 503) and attempt < retries:
                    time.sleep(2 ** attempt)
                    continue
                raise ShopifyError(f"HTTP {e.code}: {e.read().decode()[:300]}") from None
            errors = res.get("errors")
            if errors:
                if any((err.get("extensions") or {}).get("code") == "THROTTLED" for err in errors) and attempt < retries:
                    time.sleep(2 ** attempt)
                    continue
                raise ShopifyError(json.dumps(errors, ensure_ascii=False)[:800])
            return res["data"]
        raise ShopifyError("Retries exhausted")


def raise_user_errors(payload: dict, what: str) -> None:
    errs = payload.get("userErrors") or []
    if errs:
        raise ShopifyError(f"{what}: " + "; ".join(f"{e.get('field')}: {e.get('message')}" for e in errs))
