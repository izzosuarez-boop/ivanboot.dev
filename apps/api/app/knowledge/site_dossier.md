# How this site is built (public dossier for the "How it's built" mode)

Everything here is public and safe to share. Source code: https://github.com/izzosuarez-boop/ivanboot.dev
Builder: Iván (ivanboot.dev) — freelance developer focused on AI agents, automation, scraping, Shopify
and full-stack work. Hiring happens on Upwork: https://www.upwork.com/freelancers/~01d5ad771e5c598546

## What the visitor is looking at
- **tienda.ivanboot.dev** — "Ardea Skin", a fictional skincare brand built as a portfolio demo. It is a
  real, working store: real catalog, real cart, real Shopify checkout in test mode (card number 1), real
  orders in the Shopify admin. No real money moves.
- **ivanboot.dev** — Iván's portfolio (case studies of production systems).
- **This chat** — an AI agent (Claude Haiku 5.5) that is itself one of the demos.

## Architecture (one VPS, managed services around it)
- **Frontend:** one Next.js 16 app (React 19, TypeScript, Tailwind) serves BOTH the portfolio and the store.
  A small `proxy.ts` looks at the hostname: `tienda.ivanboot.dev` is rewritten internally to the store
  routes, so URLs stay clean. One codebase, one deploy, shared components.
- **Commerce:** Shopify, used **headless**. Shopify owns catalog, inventory, cart, checkout and orders;
  the storefront is custom Next.js talking to Shopify's Storefront API (GraphQL). Admin API is used by
  scripts for catalog seeding and media uploads.
- **Backend:** FastAPI (Python) at api.ivanboot.dev — hosts this agent, receives Shopify webhooks and
  runs the store owner's Telegram bot.
- **Owner bot (Telegram):** the back-office side of the demo; visitors can't see it and it answers only
  allow-listed chats. Shopify sends a webhook on every order and inventory change; the backend verifies
  Shopify's HMAC-SHA256 signature and drops duplicate deliveries.
  - *Designed not to flood the owner:* one message per event doesn't scale (at ~5,000 visitors a month that
    is several pings a day), so only actionable events are pushed right away — a product sold out or under 10
    units, orders over $150, and complaints, order issues or medical questions escalated from this chat
    (with a reference code, stored in Supabase). Everything else waits for a **daily summary at 9:00**
    (yesterday's sales vs the day before, star product, stock to watch, chat activity, cases waiting) and a
    **weekly report on Mondays** with two charts. A small scheduler inside the API keeps each report's last
    run date in Supabase, so a restart never sends twice and a report missed during downtime still goes out.
  - *Ask it in plain language:* "chart of the best sellers of the last 3 months", "top 10 customers", "how
    much did we sell this month vs last month?". Claude Haiku 5.5 picks a tool (sales, best sellers, best
    customers, stock, recent orders, chat stats); the numbers come only from Shopify's Admin API, and charts
    are rendered on the server with matplotlib in the store's palette and sent to Telegram as images — the
    model never draws or invents data. About $0.0005 per question.
  - *It can act, carefully:* the one change it can make is stock ("Vitamin C is sold out, add 40 units").
    The model can only propose; the change happens when the owner taps a Confirm button under the message.
    Only the owner's chat can do it, at most 500 units at a time; the write is a compare-and-swap (if an order
    changed the stock in between, Shopify rejects it instead of overwriting), the result is read back from
    Shopify, every attempt is logged in Supabase, and the store's cache is refreshed so the product shows as
    back on sale within seconds.
  - *Demo data:* a seeding script created a realistic 3-month history (219 orders from 44 fictitious
    customers with reserved example.com emails; growing demand, busier weekends, an October campaign spike),
    tagged `demo-seed`, without touching inventory or sending receipts — and the bot never alerts on it.
- **Database:** Supabase (managed Postgres) stores agent conversations, per-message token usage and
  cost, and cases escalated to the store owner. Row-level security is on; only the backend's secret key
  can read or write.
- **Infrastructure:** a Linux VPS in Europe running Docker Compose: Caddy (reverse proxy with automatic
  HTTPS from Let's Encrypt, HTTP/3), the Next.js container and the FastAPI container. DNS at Hostinger.
  Deploys are one command (`infra/deploy.sh`): upload source, build images on the server, restart, smoke test.
- **Media CDN:** product photos, category images and videos are stored in Shopify Files and served from
  Shopify's CDN, not from the VPS.

## Why it was built this way (decisions and trade-offs)
- **Why Shopify headless instead of a Shopify theme?** Shopify is the platform most e-commerce clients on
  Upwork use, and headless shows both skills: Shopify APIs plus a fully custom frontend (custom layout,
  animations, an AI agent embedded in the store). Shopify still handles the hard, risky parts: payments,
  taxes, inventory, checkout.
- **Why one Next.js app for two sites?** Less to deploy and maintain; the agent, design tokens and
  components are shared. Host-based routing keeps each site on its own domain.
- **Why Next.js 16 "Cache Components"?** Product data is fetched server-side with Shopify's private token
  (never exposed to the browser) and cached for minutes, so a burst of visitors costs one Shopify request.
  Pages ship an instant static shell and stream live data (stock, cart) into it.
- **Why FastAPI for the agent?** Python is the strongest ecosystem for AI work; keeping the agent server
  separate means the storefront stays fast and the agent can grow (webhooks, automations) independently.
- **Why Claude Haiku 5.5 for this chat?** It is fast and very inexpensive (about $0.10 per million input
  tokens and $0.50 per million output tokens), which matters for a public chat anyone can use. The system
  prompt is cached, so repeated context costs a tenth of the normal input price. A daily spend cap and
  per-visitor rate limits protect the budget.
- **Why Supabase?** Managed Postgres with a clean REST API and row-level security: no database server to
  run, and conversation analytics come for free.

## Interesting problems solved (real ones, with the fix)
- **The cart that silently reset.** The first cart version used Next.js Server Actions; every "Add to bag"
  quietly created a brand-new cart. Testing the full flow showed the response streamed before the cart
  cookie was set, so the browser never stored it. Fix: cart mutations moved to a Route Handler that
  builds the full response (with the cookie) before sending, plus same-origin and JSON-only CSRF checks.
- **Shopify's development-store password.** Dev stores put a password page in front of checkout, and after
  the password Shopify sends shoppers to its default theme instead of back to checkout. Fix: the cart shows
  the password and the steps before leaving the site, and the unused Shopify theme redirects anyone who
  lands on it back to their bag — so the real Shopify checkout still works end to end.
- **Honest sale badges.** A product card once showed "from $30 ~~$58~~" when only the 60 ml size was on
  sale. The logic now marks a product on sale only when a variant's compare-at price beats its own price.
- **Video that respects the visitor.** How-to videos start only when the player is fully on screen, pause
  when half of it scrolls away, and then wait for the visitor's play button. Browsers block autoplay with
  sound, so it falls back to muted playback with a "Tap for sound" button. Verified with a scripted real
  browser (Playwright) on desktop and mobile.
- **The escalation that vanished.** The first complaint test reached Telegram but never appeared in the
  database: the case was saved before its conversation row existed, so a foreign key rejected it. Fix: the
  conversation is upserted before the case. The same test revealed the HTTP client logging full request
  URLs — and Telegram puts the bot token in the URL — so those logs were silenced and the old logs dropped.
- **Stray markup in the chat.** The model occasionally ended its follow-up line with a fragment of its
  internal tool-call markup (`</parameter>`), which then showed up in the suggestion buttons. Fix: both the
  backend and the browser strip tag-like text from replies and suggestions, and a browser test checks it.

- **Letting a chatbot change real stock.** Reading data is harmless; writing is not. The model never
  writes: it prepares a proposal and the owner confirms with a button, a proposal works once and expires in
  10 minutes, and Shopify's compare-and-swap rejects a confirmation if the stock moved meanwhile. A test runs
  the whole flow against the real store (including the rejected case) and restores the original numbers.

## AI-generated media (and what it cost)
- **Product photos:** Google's Gemini image model ("Nano Banana Pro"), 2K, about $0.14 each. One shared
  art direction (natural, quiet luxury: heavy glass, champagne-gold metal, lettering printed on the pack,
  travertine stone, warm light) and a different scene per category so the grid isn't 13 copies.
- **Category videos:** Gemini Omni 1.2 Flash, 15 seconds at 1080p, about $1.56 each, with the approved
  product photo as a reference so the bottle in the video is the real one. Narration is Gemini text-to-
  speech, one line per caption, synced to captions burned in with ffmpeg. About $1.70–1.90 per category.
- **Quality control is in code, not just eyes:** labels are cropped and zoomed to check spelling (a tube
  once said "130 ML" instead of 150 — fixed by editing only that text and verifying with a pixel diff); a
  small detector flags images that came out as collages; narration is transcribed back to text to confirm
  the voice says exactly the script (it once read its own style instructions aloud).
- **Whole media budget for the demo:** roughly $10.

## External services this site uses
- **Shopify** — catalog, inventory, cart, checkout (test gateway), orders, files/CDN.
- **Anthropic Claude** — this agent (Haiku 5.5).
- **Google Gemini** — image generation, video generation, text-to-speech.
- **Supabase** — Postgres for conversations, costs and owner escalations.
- **Telegram Bot API** — owner alerts and commands (webhook mode, secret-token verified).
- **Let's Encrypt** (via Caddy) — HTTPS certificates. **GitHub** — source code.
- **Coming next:** n8n automations (order emails, abandoned carts, social posts).

## What this agent can do in the store
Recommend a routine from skin type and concerns, explain ingredients and how to use each product, check
live stock, add products to the visitor's bag, show the how-to videos, and pass complaints or medical
questions to the store owner (Telegram alert + reference code) instead of improvising. After every answer it
offers two tappable follow-up questions in the same topic.

## How Iván works (from his portfolio)
Measure before concluding; write down why each decision was made; test that a fix also fails with the
wrong input. The portfolio case studies (LLM systems in production with cost and latency budgets, a
custom P2P marketplace with an on-chain escrow on BNB Chain, an end-to-end web
scraping system that sells by the client's own rules) all follow that thread.
