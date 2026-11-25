import "server-only";
// Two versions of the portfolio from one app (2026-11-25): "upwork" (English) and "workana" (Spanish), each on
// its own domain. Hard rule from the user: nothing from one ever reaches the other, so each page gets only its
// own version's content and media from the server (client components never import a whole content file), and
// domains and profile URLs live in the server env (sites.env, outside the public repo), not in the code.
import { english } from "./portfolio";
import { spanish } from "./portfolio-es";
import type { Content } from "./types";
import type { VERSION_SEGMENTS } from "./slugs";
import portfolioMedia from "./portfolio-media.json";
import portfolioLoops from "./portfolio-loops.json";
import type { ExplainerMedia, Version } from "@/app/(portfolio)/_components/explainer-video";

export type Channel = "upwork" | "workana";
// The route segment names the version by its language, never by platform: the browser's route manifest lists
// them, and the Upwork site's files must not mention Workana (or the other way round).
export const ROUTE: Record<Channel, (typeof VERSION_SEGMENTS)[number]> = { upwork: "en", workana: "es" };
export const ROUTES = Object.values(ROUTE);
/** The version behind a route segment ("en" / "es"), or null for anything else. */
export const channelOf = (segment: string): Channel | null =>
  (Object.keys(ROUTE) as Channel[]).find((c) => ROUTE[c] === segment) ?? null;

type RawMedia = Record<string, { versions: Record<string, Version> }>;
const MEDIA = portfolioMedia as unknown as RawMedia;
const LOOPS = portfolioLoops as Record<string, { src: string; poster: string }>;

function env(ch: Channel) {
  const p = ch === "upwork" ? "UPWORK" : "WORKANA";
  return {
    site: process.env[`${p}_SITE_HOST`] ?? "",
    store: process.env[`${p}_STORE_HOST`] ?? "",
    profile: process.env[`${p}_PROFILE_URL`] ?? "",
  };
}

export type ChannelSite = Content & {
  ch: Channel;
  hireUrl: string;
  /** The version of an explainer this site plays: English and Spanish voices on Upwork, the Spanish Workana cut on Workana. */
  media: (key: string) => ExplainerMedia | undefined;
  loop: (key: string) => { src: string; poster: string } | undefined;
  /** The site's own address (canonical URL), empty when not configured (local dev). */
  origin: string;
};

export function channelSite(ch: Channel): ChannelSite {
  const e = env(ch);
  const store = e.store ? `https://${e.store}` : "/store";      // local dev: the store at /store on the same host
  const content = ch === "upwork" ? english(store) : spanish(store);
  return {
    ...content,
    ch,
    hireUrl: e.profile,
    origin: e.site ? `https://${e.site}` : "",
    // both voices on both sites (2026-11-25): each site plays its own cut of each voice (end card with its own
    // platform), never the other site's
    media: (key) => {
      const v = MEDIA[key]?.versions;
      if (!v) return undefined;
      const [en, es] = ch === "workana" ? [v["en-workana"], v["es-workana"]] : [v.en, v.es];
      if (!en && !es) return undefined;
      return { versions: { ...(en ? { en } : {}), ...(es ? { es } : {}) } };
    },
    // silent loops: the Workana site's are in Spanish, with its own addresses on screen
    // (never the English loop as a fallback there: two of them show the Upwork site's address)
    loop: (key) => LOOPS[ch === "workana" ? `${key}-es-workana` : key],
  };
}
