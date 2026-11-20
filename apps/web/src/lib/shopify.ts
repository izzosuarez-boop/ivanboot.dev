import "server-only";
import { cacheLife, cacheTag } from "next/cache";

// Storefront API, called only from the server with the PRIVATE token (never shipped
// to the browser). Results are cached in the Next.js server cache for a few minutes,
// so a burst of visitors costs one Shopify request, not hundreds.

const SHOP = process.env.SHOPIFY_SHOP;
const VERSION = process.env.SHOPIFY_API_VERSION ?? "2026-10";
const TOKEN = process.env.SHOPIFY_STOREFRONT_PRIVATE_TOKEN;
const NS = "ardea";

export type Money = { amount: string; currencyCode: string };

export type Variant = {
  id: string;
  title: string;
  availableForSale: boolean;
  quantityAvailable: number | null;
  price: Money;
  compareAtPrice: Money | null;
  selectedOptions: { name: string; value: string }[];
};

export type Product = {
  id: string;
  handle: string;
  title: string;
  productType: string;
  description: string;
  descriptionHtml: string;
  availableForSale: boolean;
  totalInventory: number | null;
  priceRange: { minVariantPrice: Money };
  compareAtPriceRange: { maxVariantPrice: Money };
  featuredImage: { url: string; altText: string | null; width: number; height: number } | null;
  variants: Variant[];
  // ardea.* metafields, parsed
  skinTypes: string[];
  concerns: string[];
  keyIngredients: string[];
  howToUse: string;
  cautions: string;
  routineStep: number;
  usageTime: string;
  texture: string;
  fragranceFree: boolean;
};

const METAFIELDS = [
  "skin_types", "concerns", "key_ingredients", "how_to_use", "cautions",
  "routine_step", "usage_time", "texture", "fragrance_free",
] as const;

const PRODUCT_FIELDS = `
  id handle title productType description descriptionHtml availableForSale totalInventory
  priceRange { minVariantPrice { amount currencyCode } }
  compareAtPriceRange { maxVariantPrice { amount currencyCode } }
  featuredImage { url altText width height }
  variants(first: 10) { nodes {
    id title availableForSale quantityAvailable
    price { amount currencyCode } compareAtPrice { amount currencyCode }
    selectedOptions { name value } } }
  metafields(identifiers: [${METAFIELDS.map((k) => `{namespace: "${NS}", key: "${k}"}`).join(", ")}]) { key value }
`;

export class StorefrontError extends Error {}

export async function storefront<T>(
  query: string,
  variables: Record<string, unknown> = {},
  opts: { buyerIp?: string | null } = {},
): Promise<T> {
  if (!SHOP || !TOKEN) throw new StorefrontError("Shopify env vars are not configured");
  const headers: Record<string, string> = { "Content-Type": "application/json", "Shopify-Storefront-Private-Token": TOKEN };
  // With the private token Shopify asks for the shopper's IP on buyer actions (cart/checkout)
  // so its bot protection and rate limits apply per shopper, not per server.
  if (opts.buyerIp) headers["Shopify-Storefront-Buyer-IP"] = opts.buyerIp;
  const res = await fetch(`https://${SHOP}.myshopify.com/api/${VERSION}/graphql.json`, {
    method: "POST",
    headers,
    body: JSON.stringify({ query, variables }),
  });
  if (!res.ok) throw new StorefrontError(`Storefront HTTP ${res.status}`);
  const json = await res.json();
  if (json.errors?.length) throw new StorefrontError(json.errors.map((e: { message: string }) => e.message).join("; "));
  return json.data as T;
}

type RawProduct = Omit<Product, "variants" | keyof ParsedMeta> & {
  variants: { nodes: Variant[] };
  metafields: ({ key: string; value: string } | null)[];
};
type ParsedMeta = Pick<Product, "skinTypes" | "concerns" | "keyIngredients" | "howToUse" | "cautions" | "routineStep" | "usageTime" | "texture" | "fragranceFree">;

function parse(raw: RawProduct): Product {
  const m = Object.fromEntries(raw.metafields.filter(Boolean).map((f) => [f!.key, f!.value]));
  const list = (v?: string): string[] => { try { return v ? JSON.parse(v) : []; } catch { return []; } };
  return {
    ...raw,
    variants: raw.variants.nodes,
    skinTypes: list(m.skin_types),
    concerns: list(m.concerns),
    keyIngredients: list(m.key_ingredients),
    howToUse: m.how_to_use ?? "",
    cautions: m.cautions ?? "",
    routineStep: Number(m.routine_step ?? 0),
    usageTime: m.usage_time ?? "",
    texture: m.texture ?? "",
    fragranceFree: m.fragrance_free === "true",
  };
}

export async function getProducts(): Promise<Product[]> {
  "use cache";
  cacheLife("minutes");
  cacheTag("products");
  const data = await storefront<{ products: { nodes: RawProduct[] } }>(
    `{ products(first: 100, sortKey: TITLE) { nodes { ${PRODUCT_FIELDS} } } }`,
  );
  return data.products.nodes.map(parse).sort((a, b) => a.routineStep - b.routineStep || a.title.localeCompare(b.title));
}

export async function getProduct(handle: string): Promise<Product | null> {
  "use cache";
  cacheLife("minutes");
  cacheTag("products", `product-${handle}`);
  const data = await storefront<{ product: RawProduct | null }>(
    `query($handle: String!) { product(handle: $handle) { ${PRODUCT_FIELDS} } }`,
    { handle },
  );
  return data.product ? parse(data.product) : null;
}

export async function getCollectionProducts(handle: string): Promise<Product[]> {
  "use cache";
  cacheLife("minutes");
  cacheTag("products", `collection-${handle}`);
  const data = await storefront<{ collection: { products: { nodes: RawProduct[] } } | null }>(
    `query($handle: String!) { collection(handle: $handle) { products(first: 50) { nodes { ${PRODUCT_FIELDS} } } } }`,
    { handle },
  );
  return (data.collection?.products.nodes ?? []).map(parse).sort((a, b) => a.title.localeCompare(b.title));
}

export function formatMoney(m: Money): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: m.currencyCode }).format(Number(m.amount));
}

// Demo routine reduced to three steps on 2026-11-20 (see scripts/shopify/catalog.json "retired")
export const STEP_LABELS: Record<number, string> = {
  1: "Cleanse",
  2: "Treat",
  3: "Weekly Mask",
};
