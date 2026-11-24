// Portfolio content: the six sections of the hub circle, clockwise from the top, and their projects.
// Videos and project images are filled in later (null = placeholder frame).

export type ProjectStatus = "Live demo" | "Case study" | "In progress";

export type Project = {
  title: string;
  status: ProjectStatus;
  summary: string | string[];  // paragraphs; "[[link]]" places the link button inline
  problem: string;
  how: string;
  result: string;
  stack: string[];
  link?: { label: string; href: string };
  demoHref?: string;            // makes the status badge a button that opens the live demo
  video?: { media: string; title: string };  // key in portfolio-media.json, shown instead of screenshots
  loop?: { media: string; label: string };   // key in portfolio-loops.json: a 6 s silent loop, shown first
  image?: string | null;
};

export type Section = {
  slug: string;
  label: string;      // section name (page header, links), also on the circle unless `ring` is set
  ring?: string;      // shorter text on the circle when `label` doesn't fit a segment
  short: string;      // compact label for small screens
  pitch: string;      // headline inside the section
  intro: string;
  // big section video above the projects; media: key in portfolio-media.json. Leave it out to show no panel at all
  video?: { title: string; media?: string; src?: string | null };
  projects: Project[];
};

const STORE = "https://tienda.ivanboot.dev";
// opens the store with the agent's chat already open and a greeting for visitors coming from the portfolio
const STORE_CHAT = `${STORE}/?ref=portfolio&chat=1`;
const REPO = "https://github.com/izzosuarez-boop/ivanboot.dev";

export const sections: Section[] = [
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
        loop: { media: "loop-sale", label: "The price monitor hits the target, the client accepts on the phone, sale complete" },
      },
      {
        title: "Social media automation",
        status: "In progress",
        summary: "Scheduled posts and replies generated from the catalog and approved by a person before publishing.",
        problem: "",
        how: "",
        result: "",
        stack: ["n8n", "Claude API", "Meta Graph API"],
      },
    ],
  },
  {
    slug: "software",
    label: "Software, APIs & QA",
    short: "Software & QA",
    pitch: "Software that is tested against the wrong answer, not just the right one.",
    intro:
      "Backends, API integrations, protocol work and test automation. Every claim backed by a test, a measurement or " +
      "a log line.",
    video: { title: "Browser tests running against the live store", src: null },
    projects: [
      {
        title: "Protocol lab",
        status: "Case study",
        summary: "A reverse-engineered TCP protocol bench: frame parser, MITM proxy with hooks, mock servers and client, and a replay and fuzzing harness.",
        problem: "Studying a legacy protocol without touching production, and trusting a parser that real clients feed in odd fragments.",
        how: "One parser shared by the proxy and every mock, an asyncio proxy that rewrites redirects, and a fuzzer that cuts the stream at every byte.",
        result: "Zero dependencies beyond the standard library; end-to-end runs with assertions in all four traffic directions.",
        stack: ["Python asyncio", "TCP", "Fuzzing", "Testing"],
      },
      {
        title: "On-chain escrow test bench",
        status: "Case study",
        summary: "A non-custodial escrow where a legal rule is a contract invariant: a buyer's money can only reach the seller or come back.",
        problem: "Custodial payment hops caused three incidents in one week; the question was what an escrow really costs per order.",
        how: "CREATE2 one-address-per-order design whose salt makes diversion impossible, compared against a single-contract design, with gas measured on two chains.",
        result: "TRON made every sale lose money; the same contract on BSC costs about $0.02 per order. Found that USDT's transfer returns false even when funds move.",
        stack: ["Solidity", "Python", "TRON", "BSC", "CREATE2"],
      },
      {
        title: "API integrations and browser tests",
        status: "Live demo",
        summary: "The plumbing behind the store: Shopify Storefront and Admin APIs, signed webhooks, Telegram, Supabase — and Playwright tests that drive a real browser.",
        problem: "Integrations break at the edges: a cookie set too late, a duplicate webhook, a token printed in a log.",
        how: "HMAC verification and de-duplication of webhooks, cart mutations in a Route Handler, scripted desktop and mobile browser runs before every release.",
        result: "Cart, chat and video behavior verified end to end on every change.",
        stack: ["REST", "GraphQL", "Webhooks", "Playwright", "FastAPI"],
        link: { label: "Source code", href: REPO },
      },
    ],
  },
  {
    slug: "scraping",
    label: "Web Scraping & Data",
    short: "Scraping",
    pitch: "Data collected reliably, matched intelligently and delivered where it is useful.",
    intro: "Scrapers that respect each site's rules, survive layout changes and turn pages into clean, matched data.",
    video: { title: "Coming soon", src: null },
    projects: [
      {
        title: "Competitor price radar",
        status: "In progress",
        summary: "Prices from permitted competitor sites, matched to the store's products with an LLM and shown as a live dashboard.",
        problem: "",
        how: "",
        result: "",
        stack: ["Python", "Playwright", "Claude API", "Supabase"],
      },
    ],
  },
  {
    slug: "ai-media",
    label: "AI Media",
    short: "AI Media",
    pitch: "Product photos and videos made with AI — and checked in code.",
    intro:
      "Generated images, videos and voice with one art direction, and quality control that does not rely on eyes alone.",
    video: { title: "How the Ardea Skin photos and videos were made", src: null },
    projects: [
      {
        title: "Ardea Skin product photography",
        status: "Live demo",
        summary: "Thirteen product photos and three category covers for a fictional brand, with one shared art direction and a different scene per category.",
        problem: "Generated packshots tend to look like a pharmacy, misspell labels or come out as collages.",
        how: "A written art direction (heavy glass, champagne-gold metal, printed lettering, travertine), approved references, labels cropped and zoomed letter by letter, and a detector that flags collages.",
        result: "About $0.14 per image; a wrong “130 ML” fixed by editing only that text and verified with a pixel diff.",
        stack: ["Gemini image", "Python", "Pillow", "Shopify Files"],
        link: { label: "See them in the store", href: STORE },
      },
      {
        title: "Category videos with narration",
        status: "Live demo",
        summary: "15-second how-to videos with the real product, narration and burned-in captions.",
        problem: "The bottle in a generated video must be the real one, and the voice must say exactly the script, in sync with the image.",
        how: "Approved photo as video reference, one narration line per caption, transcription back to text to check the voice, assembly with ffmpeg.",
        result: "About $1.70–1.90 per category; the whole demo's media budget was roughly $10.",
        stack: ["Gemini video", "Gemini TTS", "ffmpeg", "Python"],
        link: { label: "Watch in the store", href: STORE },
      },
    ],
  },
  {
    slug: "web-shopify",
    label: "Web & Shopify",
    short: "Web & Shopify",
    pitch: "Fast, custom storefronts on top of the commerce platform clients already trust.",
    intro:
      "Headless Shopify with a custom Next.js frontend: Shopify keeps payments, inventory and checkout; the experience " +
      "is fully yours.",
    video: { title: "A tour of tienda.ivanboot.dev, from catalog to checkout", src: null },
    projects: [
      {
        title: "Ardea Skin — headless Shopify store",
        status: "Live demo",
        summary: "A working store for a fictional skincare brand: real catalog, cart and Shopify checkout in test mode, with an AI advisor built in.",
        problem: "Show both sides a client needs: solid Shopify integration and a frontend that does not look like every other theme.",
        how: "Next.js 16 with server-side Storefront API calls (private token never reaches the browser), cached product data, host-based routing for two sites in one app.",
        result: "Instant static shells with live stock streamed in; a burst of visitors costs one Shopify request.",
        stack: ["Shopify Storefront API", "Next.js 16", "React 19", "Tailwind", "TypeScript"],
        link: { label: "Open the store", href: STORE },
      },
      {
        title: "One-VPS production setup",
        status: "Live demo",
        summary: "The whole site — portfolio, store and API — on one Linux server with Docker Compose and automatic HTTPS.",
        problem: "Keep hosting cheap and simple without giving up HTTPS, zero-downtime-ish deploys and a smoke test.",
        how: "Caddy reverse proxy with Let's Encrypt and HTTP/3, Next.js and FastAPI containers, one-command deploy that builds on the server and checks the result.",
        result: "Deploys in one command; media served from Shopify's CDN, not the server.",
        stack: ["Docker Compose", "Caddy", "Linux", "Let's Encrypt"],
        link: { label: "Source code", href: REPO },
      },
    ],
  },
];

export const sectionBySlug = (slug: string) => sections.find((s) => s.slug === slug);

// About card (opened from the photo in the hub). Empty fields are hidden until filled in.
// The hub's intro video, beside the circle (2026-11-22). `media` is its key in portfolio-media.json.
export const hubIntro = {
  eyebrow: "Start here",
  title: "How I put AI to work for you and plug its tools into your workflows to make you more productive.",
  videoTitle: "How AI agents fit into your work, in 70 seconds",
  media: "ai-agents-overview",
};

export const about = {
  name: "Iván",
  role: "AI engineer & automation developer",
  bio:
    "I build AI agents, automations and the software around them — from production LLM systems and scraping " +
    "pipelines to Shopify stores and 24/7 Linux workers. I measure before I conclude and write down why each " +
    "decision was made, so clients know what they are paying for.",
  education: [] as { title: string; place: string; years: string }[],
  highlights: [
    "LLM systems in production on Anthropic and DeepSeek",
    "Headless Shopify, Next.js and FastAPI",
    "Bots and automation with Telegram, webhooks and n8n",
    "Linux servers, Docker and networking",
  ],
  skills: ["Claude / LLM APIs", "AI agents & tool use", "Python", "TypeScript", "Next.js", "FastAPI", "Shopify",
    "Web scraping", "Playwright", "Supabase / Postgres", "Docker", "Linux"],
};
