// English portfolio content (the Upwork site): the four sections of the hub circle, clockwise from the top, and
// their projects. The Spanish version (Workana site) is portfolio-es.ts, with the same slugs and structure.
// 2026-11-23 (user): the scraping section was dropped (scraping lives in section 2) and AI Media + Web & Shopify
// were merged. Old URLs redirect in next.config.ts.
import type { About, Content, HubIntro, Section, Ui } from "./types";

const GH = "https://github.com/izzosuarez-boop";

/** The English version (Upwork site). `store` is the demo store's address for this version (server env). */
export function english(store: string): Content {
  // opens the store with the agent's chat already open and a greeting for visitors coming from the portfolio
  const STORE_CHAT = `${store}/?ref=portfolio&chat=1`;
  const sections: Section[] = [
  {
    slug: "ai-agents",
    label: "AI Agents & LLMs",
    short: "AI Agents",
    pitch: "AI agents: systems that think, plan and act.",
    intro:
      "Beyond a chat: from asking for things to delegating the work. Today AI agents work for you — integrated " +
      "into your platforms and workflows, they act as a force multiplier.",
    // same layout as section 2 (user, 2026-11-23): the explainer is the big section video; the card shows a loop
    video: { media: "ai-agents", title: "The store agent and the owner's Telegram agent, in 67 seconds" },
    projects: [
      {
        title: "Ardea Skin store agent",
        status: "Live demo",
        summary: [
          "A demo agent you can try live on the store I built for Shopify clients: [[link]]",
          "Ideal as the first point of contact for customers who want to know more about your products and your "
            + "site, and a powerful agent connected to your platform, your apps and third-party tools that simplifies "
            + "running your business.",
          "As part of my portfolio it also answers technical questions about the site, its structure and the "
            + "technologies it was built with, without exposing sensitive or confidential information.",
        ],
        problem: "Users want a system that solves things, not a chat that answers with simple rules. The store owner "
          + "wants an agent they can delegate work to, ask for information and trust to run the site by their "
          + "guidelines: what a person would do today, handed to an AI agent, all in one place.",
        how: "Claude Haiku 5.5 with tools that read Shopify (catalog, stock, cart) and a cached system prompt. Complaints and medical questions are escalated to the owner with a reference code. Daily spend cap and per-visitor rate limits.",
        result: "About $0.0002–0.001 per turn; conversations, token usage and cost are logged in Supabase and a browser "
          + "test checks the full flow. What it does today: recommends routines and adds products to the bag; on the "
          + "owner's side, in Telegram, it restocks or adjusts stock (always after a Confirm tap), builds charts, sends "
          + "a daily summary and a weekly report, remembers the conversation, and escalates complaints, order issues "
          + "and medical questions from the store chat.",
        stack: ["Claude API", "Tool use", "FastAPI", "Shopify Storefront API", "Shopify Admin API", "Telegram Bot API", "Supabase", "Playwright"],
        link: { label: "Try it in the store", href: STORE_CHAT },
        demoHref: STORE_CHAT,
        repos: [{ label: "Code on GitHub", href: `${GH}/ardea-skin` }],
        loop: { media: "loop-store", label: "The Ardea Skin store and its AI agent: browse, ask, added to the bag" },
      },
    ],
  },
  {
    slug: "automation",
    // renamed 2026-11-23 (user). The full name is too long for a circle segment (320 px on a 288 px arc on a
    // laptop), so the circle shows `ring`
    label: "Web Scraping, Software Automation & Data",
    ring: "Scraping, Automation & Data",
    short: "Automation",
    pitch: "Bots that do the routine work and automate your work from start to finish.",
    intro:
      "Today, more than ever, it is possible to build workflows with minimal human intervention. Software works " +
      "24/7; a person can't. Delegate everything you can automate to software or AI agents: systematic work, " +
      "gathering information, analyzing it and making decisions by your own guidelines.",
    video: { media: "automation-overview", title: "A real client case: game-currency sales automated end to end, in 86 seconds" },
    projects: [
      {
        // replaced the Telegram owner bot card 2026-11-23 (user); text approved as written
        title: "End-to-end web scraping: from data to decisions",
        status: "Case study",
        summary: "The value of web scraping isn't in collecting data but in using it well: wiring it into scripts and "
          + "bots that act on the client's own rules.",
        problem: "Many decisions depend on information that changes by the minute, and one person can't watch it all "
          + "day. This case is selling in-game currency, but the same pattern fits trading, online groceries, airlines, "
          + "hotel search, real estate and job boards: manual work that becomes far more profitable once automated. It "
          + "only makes sense when the platform has no API; if it has one, the right job is an API integration.",
        how: "Python throughout. Prices are read without a browser: the page ships its data as embedded JSON, so "
          + "reading is fast and light. Playwright drives a real Chrome only to sell, picking the server and filling in "
          + "the form. A desktop interface (Tkinter) runs price reading and the browser on separate threads so it never "
          + "freezes. Data goes to CSV and JSON, or to Excel or a SQL or NoSQL database if the client needs it. I also "
          + "work in Node.js and C# when a project calls for it.",
        result: "The client sets a minimum price and an amount. The software checks 7 servers across 3 games every "
          + "minute, decides when to sell, prepares the sale and alerts the client, who just confirms. Every step is "
          + "logged, and when something goes wrong (an expired session, a server that stops buying) it reports it "
          + "instead of failing silently.",
        stack: ["Python", "Playwright", "Chrome", "Tkinter", "Threading", "CSV / JSON"],
        repos: [{ label: "Code on GitHub", href: `${GH}/web-scraping-automation` }],
        loop: { media: "loop-sale", label: "The price monitor hits the target, the client accepts on the phone, sale complete" },
      },
    ],
  },
  {
    slug: "web-api",           // was "software" / "Software, APIs & QA" until 2026-11-23 (user)
    label: "Web & API Integration",
    short: "Web & APIs",
    // headline and intro rewritten 2026-11-24 (user asked for a proposal that fits "Web & API Integration")
    pitch: "Websites built to measure, connected to every service your business runs on.",
    intro:
      "Custom web platforms and API integrations: payments, notifications, AI and smart contracts working together in " +
      "one product, from the first sketch to production.",
    // KamasMarket end to end: its APIs, smart contracts and AI agent (made in code, 2026-11-23)
    video: { media: "web-api-overview", title: "KamasMarket end to end: nine API integrations, smart contracts and an AI agent, in 115 seconds" },
    projects: [
      {
        // replaced "Protocol lab" 2026-11-23 (user's text, checked against the KamasMarket code: Caddy at the edge
        // behind Cloudflare, Redis shared by 3 workers for listing cache + rate limits, OCR bot with Claude as an
        // advisory second check, CREATE2 escrow on BNB Chain that can only pay the seller or refund the buyer)
        title: "A website built to measure",
        status: "Case study",
        summary: "A website built around the client's needs, designed to be easy for its users and to solve a real "
          + "market problem.",
        problem: "The client asked for a complete product: a site with user accounts that works as a peer-to-peer "
          + "marketplace, where sellers list their products (here, an online game's items and currency) and buyers "
          + "purchase and pay without leaving the platform. The site is the middleman of every trade and earns a "
          + "commission on each sale.",
        how: "I chose technologies for speed and simplicity, and for full control when the client asked for changes "
          + "before going live. FastAPI for the backend, with Supabase (Postgres) as the database. Caddy as the "
          + "production gateway: it serves HTTPS and is the only way in to the backend, behind Cloudflare. Redis, "
          + "shared by the server's workers, caches the heaviest listings and keeps rate limits consistent when many "
          + "users connect at once. At the core of every trade, a smart contract written in Solidity on BNB Chain: the "
          + "payment is verified on the blockchain, and the contract pays the seller or refunds the buyer as the "
          + "backend reports, with no third option. A separate program, using computer vision and OCR with a second "
          + "check by AI, runs on its own, coordinated through the API, and receives and delivers the products inside "
          + "the game according to each payment's status.",
        result: "A product with three parts working together: the smart contract, the AI-assisted in-game software and "
          + "the backend that creates and manages the orders, many at a time, with each task handed to a single bot so "
          + "nothing is done twice. On top, an AI agent connected to the site and to every order, so each user always "
          + "knows where their product and their money are. A constant flow of buying and selling in a secure "
          + "environment.",
        stack: ["FastAPI", "Supabase", "Redis", "Caddy", "Cloudflare", "Solidity", "BNB Chain", "Docker", "DeepSeek API", "Claude API"],
        repos: [
          { label: "Smart contract", href: `${GH}/escrow-smart-contract` },
          { label: "AI agent", href: `${GH}/llm-support-agent` },
          { label: "Infrastructure", href: `${GH}/marketplace-infra` },
        ],
        loop: { media: "loop-kamas", label: "KamasMarket: an offer is picked, the order moves step by step, the contract pays the seller" },
      },
    ],
  },
  {
    slug: "ai-media-shopify",  // merged from "ai-media" and "web-shopify" 2026-11-23 (user)
    label: "AI, Social Media & Shopify",  // renamed by the user 2026-11-24 (was "AI Media & Shopify")
    short: "Media & Shopify",
    // headline, intro and the two cards rewritten by the user (2026-11-24); photography, category videos and
    // the VPS setup cards were removed
    pitch: "AI-generated media: meaningful production that sells ideas.",
    intro:
      "AI content is worth making when its meaning reaches your customers and users in a way that is consistent and " +
      "easy to understand, while what you communicate builds an identity of your own.",
    // how the portfolio's AI content is made: idea, consistency, corrections, code, Ardea Skin, social media, budget
    video: { media: "media-overview", title: "How the content is made: idea, consistency, real corrections and a budget under $25, in 143 seconds" },
    projects: [
      {
        title: "AI & Social Media: from idea to product",
        status: "Case study",
        summary: "Content creation has become one of the fastest-growing fields of recent years. Today, beyond what gets "
          + "made, what gives content its value is what it conveys and how that message is understood by the people it reaches.",
        problem: "Making content keeps getting easier, so social networks, media outlets and websites flood people with more "
          + "information than they can take in. Selling an idea through your site is not the same when twenty other places "
          + "are trying to do it too. That is why, more than ever, what matters is not the medium that carries the idea but "
          + "the idea itself: presented so it is easy to understand and digest, and so it builds an identity people "
          + "remember in the medium and long term.",
        how: "Every video on this site follows a structure built to convey one idea and what I want to sell. I used "
          + "Google's AI models (Gemini Omni and its Flash version, plus Gemini for images and voice), Seedance and "
          + "DaVinci AI, and coding tools like Claude Opus 5.5. That last part matters: a good result comes from a solid "
          + "base and a model that drives the whole creative process during development. Code doesn't replace the AI; "
          + "it complements it.",
        result: "Videos with an intent and an idea behind them. This site exists to sell my portfolio and my skills to "
          + "anyone who needs to build, improve, or simply find talent for their projects, and that is what every video "
          + "tries to convey: a problem, its solution and my role in it, while showing what I can do.",
        stack: ["Gemini Omni", "Gemini image", "Gemini TTS", "Seedance", "DaVinci AI", "Claude Opus 5.5", "ffmpeg", "Playwright"],
        repos: [{ label: "Code on GitHub", href: `${GH}/ai-media` }],
        loop: { media: "loop-media", label: "The idea, consistent frames, a real correction, ready to post" },
      },
      {
        title: "Ardea Skin: a Shopify store with an identity of its own",
        status: "Live demo",
        summary: "A working store for a fictional skincare brand: real catalog, cart and Shopify checkout in test mode, with an AI advisor built in.",
        problem: "Every client wants something made to their taste. Most online stores offer useful features, but cast "
          + "from a mold made for everyone. That is where the need comes from: building an identity of its own on top of "
          + "a site, one that represents what the client wants to sell to their users.",
        how: "Frontend: Next.js 16, React 19, TypeScript and Tailwind 4, the same app that serves this portfolio, so "
          + "there is one codebase and one deploy. Shopify handles the catalog, inventory, checkout, orders, and the "
          + "images and videos (from its own CDN). The chat agent runs on Claude Haiku 5.5, with measured costs and "
          + "per-visitor limits against spam. Supabase (managed Postgres) stores the chat conversations, the token cost "
          + "of every message, the escalated cases and the date of the last reports, so none is sent twice. A Telegram "
          + "integration runs the store from outside, with an AI agent between the two.",
        result: "A site made to measure for a potential client. The products are demos, but it shows an identity that "
          + "carries into every part of the store and every new product, making the store much simpler and more "
          + "automated to run without losing the human touch users look for.",
        stack: ["Shopify Storefront API", "Next.js 16", "React 19", "Tailwind 4", "TypeScript", "Claude API", "Supabase", "Telegram"],
        link: { label: "Open the store", href: store },
        repos: [{ label: "Code on GitHub", href: `${GH}/ardea-skin` }],
        loop: { media: "loop-ardea", label: "Ardea Skin: one identity on every page, and the store run from Telegram" },
      },
    ],
  },
];

  // The hub's intro video, beside the circle (2026-11-22). `media` is its key in portfolio-media.json.
  const hubIntro: HubIntro = {
  eyebrow: "Start here",
  title: "How I put AI to work for you and plug its tools into your workflows to make you more productive.",
  videoTitle: "How AI agents fit into your work, in 70 seconds",
  media: "ai-agents-overview",
};

  // About card (opened from the photo in the hub). Empty fields are hidden until filled in.
  const about: About = {
  name: "Iván",
  role: "AI engineer & automation developer",
  bio:
    "I build AI agents, automations and the software around them — from production LLM systems and scraping " +
    "pipelines to Shopify stores and 24/7 Linux workers. I measure before I conclude and write down why each " +
    "decision was made, so clients know what they are paying for.",
  education: [],
  highlights: [
    "LLM systems in production on Anthropic and DeepSeek",
    "Headless Shopify, Next.js and FastAPI",
    "Bots and automation with Telegram, webhooks and n8n",
    "Linux servers, Docker and networking",
  ],
  skills: ["Claude / LLM APIs", "AI agents & tool use", "Python", "TypeScript", "Next.js", "FastAPI", "Shopify",
    "Web scraping", "Playwright", "Supabase / Postgres", "Docker", "Linux"],
};

  return { lang: "en", sections, hubIntro, about, ui: UI };
}

const UI: Ui = {
  srTitle: "Iván — AI agents, automation and full-stack development",
  roleLine: "AI engineer · automation developer",
  allWork: "All work",
  hire: "Hire me on Upwork",
  hireTitle: "Have a project like this?",
  hireBody: "Tell me what you need on Upwork and I'll reply with a plan and an estimate.",
  chooseArea: "Choose an area of work",
  aboutMe: "About me",
  aboutOf: (name) => `About ${name}`,
  sceneAlt: (name) => `${name} working at a desk with three monitors`,
  portraitAlt: (name) => `Portrait of ${name}`,
  close: "Close",
  education: "Education",
  highlights: "Highlights",
  skills: "Skills",
  introVideo: "Intro video",
  explainerVideo: "Explainer video",
  projects: "Projects",
  otherAreas: "Other areas",
  areasOfWork: "Areas of work",
  problem: "The problem",
  how: "How I built it",
  result: "Result",
  status: { "Live demo": "Live demo", "Case study": "Case study", "In progress": "In progress" },
  screenshotsSoon: "Screenshots coming soon",
  videoSoon: "Explainer video · coming soon",
  onGithub: (label) => `${label} on GitHub`,
  player: { voice: "Voice", subtitles: "Subtitles", tapForSound: "Tap for sound", fullScreen: "Full screen", exitFullScreen: "Exit full screen" },
};

