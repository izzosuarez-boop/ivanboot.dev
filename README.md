# ivanboot.dev

**Live: [ivanboot.dev](https://ivanboot.dev)** · the store: [tienda.ivanboot.dev](https://tienda.ivanboot.dev)

How I put AI to work for you and plug its tools into your workflows to make you more productive.

I build AI agents, automations and the software around them — from production LLM systems and scraping pipelines to
Shopify stores and 24/7 Linux workers. I measure before I conclude and write down why each decision was made, so
clients know what they are paying for.

This repo is the whole site: the portfolio, the Ardea Skin demo store and the API, in one codebase and one deploy.

## The four sections

| Section | What it shows | Repo |
|---|---|---|
| [AI Agents & LLMs](https://ivanboot.dev/ai-agents) | AI agents: systems that think, plan and act. The Ardea Skin store agent and the owner's Telegram agent | [ardea-skin](https://github.com/izzosuarez-boop/ardea-skin) |
| [Web Scraping, Software Automation & Data](https://ivanboot.dev/automation) | Bots that do the routine work and automate your work from start to finish | [web-scraping-automation](https://github.com/izzosuarez-boop/web-scraping-automation) |
| [Web & API Integration](https://ivanboot.dev/web-api) | Websites built to measure, connected to every service your business runs on: KamasMarket | [llm-support-agent](https://github.com/izzosuarez-boop/llm-support-agent) · [marketplace-infra](https://github.com/izzosuarez-boop/marketplace-infra) · [escrow-smart-contract](https://github.com/izzosuarez-boop/escrow-smart-contract) |
| [AI, Social Media & Shopify](https://ivanboot.dev/ai-media-shopify) | AI-generated media: meaningful production that sells ideas | [ai-media](https://github.com/izzosuarez-boop/ai-media) · [ardea-skin](https://github.com/izzosuarez-boop/ardea-skin) |

## What's in this repo

| Path | What it is |
|---|---|
| `apps/web/` | Next.js 16, React 19, TypeScript and Tailwind 4: the portfolio on ivanboot.dev and the store on tienda.ivanboot.dev (same app, routed by host) |
| `apps/api/` | FastAPI: the store agent (Claude Haiku 5.5), the owner's Telegram bot, Shopify webhooks and reports, Supabase |
| `scripts/media/`, `scripts/images/` | Every video and image of the site, made with AI and corrected in code |
| `scripts/shopify/`, `scripts/telegram/`, `scripts/db/` | Store catalog, bot setup and database migrations |
| `scripts/tests/` | Browser tests (Playwright) of the portfolio, the videos and the store agent |
| `infra/` | Docker Compose and Caddy on one Linux VPS, with automatic HTTPS and a one-command deploy |

Older write-ups kept here: `escrow-smart-contract/`, `linux-fleet-guide/`, `llm-production-case-study/`.
