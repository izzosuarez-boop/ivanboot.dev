"""ivanboot.dev API — the Ardea Skin agent, Shopify webhooks and the owner's Telegram bot."""
from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager

import anthropic
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import agent, config, db, guard, notify, reports, shopify_admin, webhooks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
# httpx logs full request URLs at INFO, and Telegram puts the bot token in the URL: keep it out of the logs.
logging.getLogger("httpx").setLevel(logging.WARNING)
STARTED_AT = time.time()
VERSION = os.getenv("APP_VERSION", "dev")

@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(reports.scheduler())  # daily summary + weekly report for the owner
    yield
    task.cancel()


app = FastAPI(title="ivanboot API", version=VERSION, docs_url="/docs", redoc_url=None, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ivanboot.dev", "https://tienda.ivanboot.dev", "http://localhost:3000", "http://127.0.0.1:3123"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(webhooks.router)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=config.MAX_MESSAGE_CHARS)
    conversation_id: str | None = Field(default=None, max_length=64)
    mode: str | None = Field(default=None, pattern="^(skin|builder)$")
    ref: str | None = Field(default=None, max_length=40)


def friendly(status: int, msg: str) -> JSONResponse:
    return JSONResponse({"error": msg}, status_code=status)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok", "version": VERSION, "uptime_s": int(time.time() - STARTED_AT),
        "shopify_configured": bool(config.SHOPIFY_SHOP and config.SHOPIFY_STOREFRONT_PRIVATE_TOKEN),
        "agent_configured": bool(config.ANTHROPIC_API_KEY), "db_configured": db.enabled(),
        "admin_configured": shopify_admin.enabled(), "telegram_configured": notify.enabled(),
    }


@app.post("/chat")
async def chat(body: ChatIn, request: Request):
    if not config.ANTHROPIC_API_KEY:
        return friendly(503, "The assistant is being set up. Please come back soon.")
    ip = request.client.host if request.client else "unknown"  # real client IP via Caddy + --proxy-headers
    visitor = guard.visitor_hash(ip, request.headers.get("user-agent", ""))

    if (why := guard.rate_limited(visitor)) is not None:
        return friendly(429, "You're sending messages very fast — give me a minute." if why == "minute"
                        else "You've reached the hourly chat limit for this demo. Please try again later.")
    if await guard.over_budget():
        return friendly(503, "The demo assistant has reached today's budget. It resets at midnight UTC — "
                             "meanwhile, everything else in the store works.")

    conv = agent.get_conversation(body.conversation_id, visitor)
    if conv.user_turns >= config.MAX_USER_TURNS:
        return friendly(429, "This conversation is getting long — please start a new chat.")
    try:
        return await agent.chat(conv, body.message.strip(), body.mode, body.ref)
    except anthropic.RateLimitError:
        return friendly(503, "The assistant is busy right now. Please try again in a moment.")
    except anthropic.APIStatusError as e:
        logging.getLogger("agent").error("anthropic %s: %s", e.status_code, str(e)[:300])
        return friendly(502, "The assistant had a hiccup. Please try again.")
    except anthropic.APIConnectionError:
        return friendly(502, "The assistant can't be reached right now. Please try again.")
