// The four sections, clockwise from the top of the hub circle. Both versions of the site (Upwork in English,
// Workana in Spanish) use the same slugs, so the circle's geometry and the URLs are shared.
export const SLUGS = ["ai-agents", "automation", "web-api", "ai-media-shopify"] as const;

// Internal route segment of each version (see content/channel.ts). Pages are prerendered at /en/... and /es/...
// but visitors see /...: anything that reads the pathname drops this segment so server and browser agree.
export const VERSION_SEGMENTS = ["en", "es"] as const;
export const visiblePath = (pathname: string) => {
  const parts = pathname.split("/").filter(Boolean);
  if ((VERSION_SEGMENTS as readonly string[]).includes(parts[0])) parts.shift();
  return parts;
};

/** What the circle and the top bar need from a version: labels only, no other content. */
export type NavItem = { slug: string; label: string; ring?: string; short: string };
export type ShellUi = { name: string; roleLine: string; allWork: string; hire: string; hireUrl: string; areasOfWork: string; lang: "en" | "es" };
