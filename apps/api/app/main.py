"""ivanboot.dev API — home of the AI agent, Shopify webhooks and automations.

v0: health endpoint only. The agent (Claude + tools over the Shopify catalog) and the
webhook receivers land here next.
"""
from __future__ import annotations

import os
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

STARTED_AT = time.time()
VERSION = os.getenv("APP_VERSION", "dev")

app = FastAPI(title="ivanboot API", version=VERSION, docs_url="/docs", redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ivanboot.dev", "https://tienda.ivanboot.dev", "http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": VERSION,
        "uptime_s": int(time.time() - STARTED_AT),
        "shopify_configured": bool(os.getenv("SHOPIFY_SHOP") and os.getenv("SHOPIFY_CLIENT_ID")),
    }
