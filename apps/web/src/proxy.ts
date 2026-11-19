import { NextResponse, type NextRequest } from "next/server";

// One Next.js app, two sites:
//   ivanboot.dev         -> portfolio (app/page.tsx ...)
//   tienda.ivanboot.dev  -> Ardea Skin demo store (app/store/...)
// The store host is rewritten internally to /store/*, so its URLs stay clean
// (tienda.ivanboot.dev/products/x). On the portfolio host, /store is redirected
// to the store's own domain so there is exactly one public URL per page.
const STORE_HOST = process.env.STORE_HOST ?? "tienda.ivanboot.dev";

export function proxy(request: NextRequest) {
  const host = (request.headers.get("host") ?? "").split(":")[0];
  const { pathname, search } = request.nextUrl;

  if (host === STORE_HOST) {
    if (pathname.startsWith("/store")) {
      // Old/duplicated path on the store host: strip the prefix
      const clean = pathname.replace(/^\/store/, "") || "/";
      return NextResponse.redirect(new URL(clean + search, request.url), 308);
    }
    const url = request.nextUrl.clone();
    url.pathname = `/store${pathname === "/" ? "" : pathname}`;
    return NextResponse.rewrite(url);
  }

  // Portfolio host: send /store/* to the store domain (except locally, where
  // there is no subdomain and /store is the way to preview the shop).
  if (pathname.startsWith("/store") && host !== "localhost" && host !== "127.0.0.1") {
    const clean = pathname.replace(/^\/store/, "") || "/";
    return NextResponse.redirect(`https://${STORE_HOST}${clean}${search}`, 308);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:png|jpg|jpeg|svg|webp|ico|txt|xml)$).*)"],
};
