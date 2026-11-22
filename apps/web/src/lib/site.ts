// Public site configuration. Profile links are optional: an empty value hides its button.
export const site = {
  name: "Iván",
  handle: "ivanboot",
  domain: "ivanboot.dev",
  storeUrl: process.env.NEXT_PUBLIC_STORE_URL ?? "https://tienda.ivanboot.dev",
  upworkUrl: process.env.NEXT_PUBLIC_UPWORK_URL || "https://www.upwork.com/freelancers/~01d5ad771e5c598546",
  workanaUrl: process.env.NEXT_PUBLIC_WORKANA_URL ?? "",
};

// Store links: "" in production (tienda.ivanboot.dev/products/x),
// "/store" locally (localhost:3000/store/products/x). Inlined at build time.
export const STORE_BASE = process.env.NEXT_PUBLIC_STORE_BASE ?? "/store";
export const storeHref = (path: string) => `${STORE_BASE}${path === "/" && STORE_BASE ? "" : path}` || "/";
