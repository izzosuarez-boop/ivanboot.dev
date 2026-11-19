import { site } from "@/lib/site";

type Project = {
  title: string;
  kind: string;
  status: "Live demo" | "Case study" | "In progress";
  summary: string;
  stack: string[];
  href?: string;
};

const projects: Project[] = [
  {
    title: "Ardea Skin — AI-powered Shopify store",
    kind: "E-commerce · AI agent · Automation",
    status: "Live demo",
    summary:
      "A headless Shopify store for a fictional skincare brand. Product data is modelled for an AI sales & support agent that recommends routines, builds carts and answers order questions on web, WhatsApp and Telegram.",
    stack: ["Shopify Storefront & Admin API", "Next.js", "FastAPI", "Claude API", "n8n"],
    href: site.storeUrl,
  },
  {
    title: "LLM integrations in production",
    kind: "AI agents · Cost & latency engineering",
    status: "Case study",
    summary:
      "Three production LLM systems on two providers: a function-calling support agent with measured failover, a vision model as an independent second reader, and a human-like async responder. Cost and latency budgets are design inputs, not afterthoughts.",
    stack: ["Anthropic", "DeepSeek", "Function calling", "Structured output"],
  },
  {
    title: "On-chain escrow test bench",
    kind: "Smart contracts · Measurement",
    status: "Case study",
    summary:
      "A non-custodial escrow where a legal constraint is a contract invariant. Gas measured on two chains turned a money-losing design on TRON into $0.02 per order on BSC — a decision made from numbers, not intuition.",
    stack: ["Solidity", "Python", "TRON", "BSC", "CREATE2"],
  },
  {
    title: "Protocol lab",
    kind: "Reverse engineering · Networking",
    status: "Case study",
    summary:
      "A reverse-engineered TCP protocol bench: frame parser, MITM proxy with hooks, mock servers and client, plus a replay and fuzzing harness that cuts the stream at every byte.",
    stack: ["Python asyncio", "TCP", "Fuzzing", "Testing"],
  },
  {
    title: "Fleet of headless Linux workers",
    kind: "Infrastructure · Automation",
    status: "Case study",
    summary:
      "Runbook for nine 24/7 automation workers with per-machine network egress, self-healing supervisors and a catalog of real failures — each one caught by hitting it.",
    stack: ["Linux", "systemd", "Networking", "Computer vision"],
  },
];

const upcoming = [
  { title: "WhatsApp, Telegram & email automation", note: "Order updates, abandoned carts and support on the channels customers already use." },
  { title: "Competitor price radar", note: "Scraping plus LLM product matching, shown as a live dashboard." },
  { title: "AI product videos", note: "Script, visuals and voice generated from the catalog, assembled with code." },
];

const skills = [
  "AI agents & tool use", "Claude / LLM APIs", "Workflow automation", "Web scraping",
  "Shopify (headless)", "Next.js & React", "FastAPI & Python", "Supabase / Postgres",
  "Docker & Linux", "Graphic design",
];

function StatusBadge({ status }: { status: Project["status"] }) {
  const style =
    status === "Live demo"
      ? "border-accent/40 bg-accent/10 text-accent"
      : status === "In progress"
        ? "border-accent-2/40 bg-accent-2/10 text-accent-2"
        : "border-line text-muted";
  return <span className={`rounded-full border px-2.5 py-0.5 text-xs ${style}`}>{status}</span>;
}

export default function Home() {
  const hireLinks = [
    site.upworkUrl && { label: "Hire me on Upwork", href: site.upworkUrl },
    site.workanaUrl && { label: "Hire me on Workana", href: site.workanaUrl },
  ].filter(Boolean) as { label: string; href: string }[];

  return (
    <div className="flex-1 bg-ink text-text">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-5 sm:px-6">
        <span className="font-mono text-sm text-muted">
          <span className="text-accent">~/</span>{site.handle}
        </span>
        <nav className="flex gap-5 text-sm text-muted">
          <a href="#work" className="hover:text-text">Work</a>
          <a href="#skills" className="hover:text-text">Skills</a>
          <a href={site.storeUrl} className="hover:text-text">Live demo</a>
        </nav>
      </header>

      <main>
        <section className="relative overflow-hidden">
          <div
            aria-hidden
            className="pointer-events-none absolute -top-40 left-1/2 h-[520px] w-[900px] -translate-x-1/2 rounded-full opacity-25 blur-3xl"
            style={{ background: "radial-gradient(closest-side, var(--accent), transparent), radial-gradient(closest-side, var(--accent-2), transparent)" }}
          />
          <div className="relative mx-auto max-w-6xl px-4 pb-20 pt-16 sm:px-6 sm:pt-24">
            <p className="rise font-mono text-sm text-accent">AI agents · automation · full-stack</p>
            <h1 className="rise rise-1 mt-4 max-w-3xl text-4xl font-semibold leading-tight tracking-tight sm:text-6xl">
              I build AI agents, automations and the software around them.
            </h1>
            <p className="rise rise-2 mt-6 max-w-2xl text-lg text-muted">
              Production LLM systems, scraping pipelines, Shopify stores and workflow automation —
              measured before I conclude, and documented so you know why each decision was made.
            </p>
            <div className="rise rise-3 mt-10 flex flex-wrap gap-3">
              <a
                href={site.storeUrl}
                className="rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-ink transition hover:brightness-110"
              >
                Explore the live store demo →
              </a>
              {hireLinks.map((l) => (
                <a key={l.href} href={l.href} className="rounded-full border border-line px-5 py-2.5 text-sm transition hover:border-muted">
                  {l.label}
                </a>
              ))}
              <a href="#work" className="rounded-full border border-line px-5 py-2.5 text-sm transition hover:border-muted">
                See my work
              </a>
            </div>
          </div>
        </section>

        <section id="work" className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <h2 className="text-sm font-mono uppercase tracking-widest text-muted">Selected work</h2>
          <div className="mt-8 grid gap-5 md:grid-cols-2">
            {projects.map((p, i) => {
              const Card = p.href ? "a" : "article";
              return (
                <Card
                  key={p.title}
                  {...(p.href ? { href: p.href } : {})}
                  className={`group rounded-2xl border border-line bg-ink-2 p-6 transition hover:border-muted ${i === 0 ? "md:col-span-2" : ""}`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <p className="text-xs text-muted">{p.kind}</p>
                    <StatusBadge status={p.status} />
                  </div>
                  <h3 className="mt-3 text-xl font-semibold tracking-tight">
                    {p.title}
                    {p.href && <span className="ml-2 inline-block text-accent transition group-hover:translate-x-1">→</span>}
                  </h3>
                  <p className="mt-3 text-sm leading-relaxed text-muted">{p.summary}</p>
                  <ul className="mt-5 flex flex-wrap gap-2">
                    {p.stack.map((s) => (
                      <li key={s} className="rounded-md bg-ink px-2 py-1 font-mono text-xs text-muted">{s}</li>
                    ))}
                  </ul>
                </Card>
              );
            })}
          </div>

          <h3 className="mt-14 text-sm font-mono uppercase tracking-widest text-muted">Coming next</h3>
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {upcoming.map((u) => (
              <div key={u.title} className="rounded-2xl border border-dashed border-line p-5">
                <StatusBadge status="In progress" />
                <p className="mt-3 font-medium">{u.title}</p>
                <p className="mt-1 text-sm text-muted">{u.note}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="skills" className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <h2 className="text-sm font-mono uppercase tracking-widest text-muted">What I work with</h2>
          <ul className="mt-6 flex flex-wrap gap-2.5">
            {skills.map((s) => (
              <li key={s} className="rounded-full border border-line px-4 py-2 text-sm">{s}</li>
            ))}
          </ul>
        </section>
      </main>

      <footer className="mx-auto w-full max-w-6xl border-t border-line px-4 py-8 text-sm text-muted sm:px-6">
        {site.name} · {site.domain}
      </footer>
    </div>
  );
}
