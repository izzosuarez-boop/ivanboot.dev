import { NextResponse, type NextRequest } from "next/server";

// One Next.js app, four sites (2026-11-25): two versions of the portfolio, each with its own Ardea Skin store.
//   Upwork site   (English)  -> app/(portfolio)/[ch]/... with ch = "upwork",  store -> app/store/...
//   Workana site  (Spanish)  -> app/(portfolio)/[ch]/... with ch = "workana", store -> app/store/...
// Hosts come from the server env (sites.env, outside the public repo). Nothing here sends a visitor from one
// version to the other: every request stays on the host it arrived on. The Workana hosts are also kept out of
// search results (X-Robots-Tag), since that site is reached from the Workana profile only.
const hosts = (name: string) => (process.env[name] ?? "").split(",").map((h) => h.trim().toLowerCase()).filter(Boolean);
const withWww = (list: string[]) => list.flatMap((h) => [h, `www.${h}`]);

const UPWORK_SITE = withWww(hosts("UPWORK_SITE_HOST"));
const WORKANA_SITE = withWww(hosts("WORKANA_SITE_HOST"));
const STORES = [...hosts("UPWORK_STORE_HOST"), ...hosts("WORKANA_STORE_HOST")];
const WORKANA_ALL = [...WORKANA_SITE, ...hosts("WORKANA_STORE_HOST")];
const LOCAL = ["localhost", "127.0.0.1"];

function noindex(res: NextResponse, host: string) {
  if (WORKANA_ALL.includes(host)) res.headers.set("X-Robots-Tag", "noindex, nofollow");
  return res;
}

export function proxy(request: NextRequest) {
  const host = (request.headers.get("host") ?? "").split(":")[0].toLowerCase();
  const { pathname, search } = request.nextUrl;

  if (STORES.includes(host)) {
    if (pathname.startsWith("/store")) {
      // old or duplicated path on a store host: strip the prefix
      const clean = pathname.replace(/^\/store/, "") || "/";
      return noindex(NextResponse.redirect(new URL(clean + search, request.url), 308), host);
    }
    if (pathname.startsWith("/api/revalidate")) return NextResponse.next();
    const url = request.nextUrl.clone();
    url.pathname = `/store${pathname === "/" ? "" : pathname}`;
    return noindex(NextResponse.rewrite(url), host);
  }

  if (pathname.startsWith("/api/") || pathname.startsWith("/__")) return NextResponse.next();

  // Local dev: the store at /store, the portfolio at / (DEV_CHANNEL=workana shows the Spanish version)
  if (LOCAL.includes(host) && pathname.startsWith("/store")) return NextResponse.next();

  // the version's route segment: "en" (Upwork site) or "es" (Workana site), see content/channel.ts
  const ch = WORKANA_SITE.includes(host) ? "es"
    : UPWORK_SITE.includes(host) ? "en"
      : LOCAL.includes(host) ? (process.env.DEV_CHANNEL === "workana" ? "es" : "en")
        : null;
  if (!ch) return new NextResponse("Not found", { status: 404 });
  // old /store links on a portfolio host: to the store of the same version
  const ownStore = hosts(ch === "es" ? "WORKANA_STORE_HOST" : "UPWORK_STORE_HOST")[0];
  if (pathname.startsWith("/store") && ownStore) {
    const clean = pathname.replace(/^\/store/, "") || "/";
    return noindex(NextResponse.redirect(`https://${ownStore}${clean}${search}`, 308), host);
  }
  // /en/... and /es/... are internal: never reachable as typed, on any host
  const url = request.nextUrl.clone();
  url.pathname = `/${ch}${pathname === "/" ? "" : pathname}`;
  return noindex(NextResponse.rewrite(url), host);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:png|jpg|jpeg|svg|webp|ico|txt|xml|vtt|mp4)$).*)"],
};
