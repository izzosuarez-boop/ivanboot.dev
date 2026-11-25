import type { Metadata, Viewport } from "next";
import { notFound } from "next/navigation";
import { PortfolioShell } from "../_components/portfolio-shell";
import { ROUTES, channelOf, channelSite } from "@/content/channel";

// One portfolio, two versions (2026-11-25): /en/* is served on the Upwork site's domain and /es/* on the Workana
// site's, both at the root of their domain (proxy.ts rewrites by host). Visitors never see these prefixes.

// The portfolio is dark already. Saying so (<meta name="color-scheme" content="dark">) keeps browsers with a
// forced dark mode (Chromium's auto dark, Android WebView's algorithmic darkening, Mi Browser) from repainting
// it: Mi Browser turned the hub circle's dark SVG fills light grey (2026-11-23, PLAYBOOK E30). The store is
// light and keeps its own layout.
export const viewport: Viewport = { colorScheme: "dark", themeColor: "#0b0d10" };

export function generateStaticParams() {
  return ROUTES.map((ch) => ({ ch }));
}

export async function generateMetadata({ params }: LayoutProps<"/[ch]">): Promise<Metadata> {
  const ch = channelOf((await params).ch);
  if (!ch) return {};
  const site = channelSite(ch);
  const es = site.lang === "es";
  return {
    ...(site.origin ? { metadataBase: new URL(site.origin) } : {}),
    title: { default: es ? "Iván: agentes de IA, automatización y desarrollo full-stack" : "Iván — AI agents, automation & full-stack", template: "%s" },
    description: es
      ? "Construyo agentes de IA, automatizaciones y el software que los rodea: sistemas con LLMs en producción, scraping, Shopify y automatización de flujos de trabajo."
      : "I build AI agents, automations and the software around them: production LLM systems, scraping, Shopify and workflow automation.",
    // the Workana site is reached from the Workana profile only: kept out of search results (user, 2026-11-25)
    ...(ch === "workana" ? { robots: { index: false, follow: false } } : {}),
  };
}

export default async function ChannelLayout({ children, params }: LayoutProps<"/[ch]">) {
  const ch = channelOf((await params).ch);
  if (!ch) notFound();
  const site = channelSite(ch);
  return (
    <PortfolioShell
      nav={site.sections.map(({ slug, label, ring, short }) => ({ slug, label, ring, short }))}
      ui={{
        name: site.about.name, roleLine: site.ui.roleLine, allWork: site.ui.allWork, hire: site.ui.hire,
        hireUrl: site.hireUrl, areasOfWork: site.ui.areasOfWork, lang: site.lang,
      }}
    >
      {children}
    </PortfolioShell>
  );
}
