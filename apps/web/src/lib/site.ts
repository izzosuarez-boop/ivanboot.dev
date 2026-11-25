// Store links: "" in production (tienda.<domain>/products/x), "/store" locally (localhost:3000/store/products/x).
// Inlined at build time. Domains and hiring profiles are not here: see content/channel.ts and sites.env.
export const STORE_BASE = process.env.NEXT_PUBLIC_STORE_BASE ?? "/store";
export const storeHref = (path: string) => `${STORE_BASE}${path === "/" && STORE_BASE ? "" : path}` || "/";
