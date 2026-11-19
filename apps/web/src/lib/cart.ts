import "server-only";
import { cookies, headers } from "next/headers";
import { storefront, type Money } from "./shopify";

// The cart lives in Shopify; the browser only keeps its id in an httpOnly cookie.
export const CART_COOKIE = "ardea_cart";

export type CartLine = {
  id: string;
  quantity: number;
  cost: { totalAmount: Money };
  merchandise: {
    id: string;
    title: string;
    quantityAvailable: number | null;
    price: Money;
    selectedOptions: { name: string; value: string }[];
    image: { url: string; altText: string | null } | null;
    product: { handle: string; title: string };
  };
};

export type Cart = {
  id: string;
  checkoutUrl: string;
  totalQuantity: number;
  cost: { subtotalAmount: Money; totalAmount: Money };
  lines: CartLine[];
};

const CART_FIELDS = `
  id checkoutUrl totalQuantity
  cost { subtotalAmount { amount currencyCode } totalAmount { amount currencyCode } }
  lines(first: 50) { nodes {
    id quantity cost { totalAmount { amount currencyCode } }
    merchandise { ... on ProductVariant {
      id title quantityAvailable price { amount currencyCode }
      selectedOptions { name value }
      image { url altText }
      product { handle title } } } } }
`;

type RawCart = Omit<Cart, "lines"> & { lines: { nodes: CartLine[] } };
type Problem = { message: string };
type MutationPayload = { cart: RawCart | null; userErrors: Problem[]; warnings?: Problem[] };

const toCart = (raw: RawCart | null): Cart | null => (raw ? { ...raw, lines: raw.lines.nodes } : null);

export async function buyerIp(): Promise<string | null> {
  const h = await headers();
  return h.get("x-forwarded-for")?.split(",")[0]?.trim() || h.get("x-real-ip");
}

/** Read the visitor's cart (never cached: it is per person). */
export async function getCart(): Promise<Cart | null> {
  const id = (await cookies()).get(CART_COOKIE)?.value;
  if (!id) return null;
  try {
    const data = await storefront<{ cart: RawCart | null }>(
      `query($id: ID!) { cart(id: $id) { ${CART_FIELDS} } }`, { id }, { buyerIp: await buyerIp() });
    return toCart(data.cart); // null when the cart expired or was turned into an order
  } catch {
    return null;
  }
}

async function mutate(name: string, query: string, variables: Record<string, unknown>) {
  const data = await storefront<Record<string, MutationPayload>>(query, variables, { buyerIp: await buyerIp() });
  const payload = data[name];
  const problems = [...(payload.userErrors ?? []), ...(payload.warnings ?? [])].map((p) => p.message);
  return { cart: toCart(payload.cart), problems };
}

export const cartCreate = (lines: { merchandiseId: string; quantity: number }[]) =>
  mutate("cartCreate",
    `mutation($lines: [CartLineInput!]) { cartCreate(input: { lines: $lines }) {
       cart { ${CART_FIELDS} } userErrors { message } warnings { message } } }`, { lines });

export const cartLinesAdd = (cartId: string, lines: { merchandiseId: string; quantity: number }[]) =>
  mutate("cartLinesAdd",
    `mutation($cartId: ID!, $lines: [CartLineInput!]!) { cartLinesAdd(cartId: $cartId, lines: $lines) {
       cart { ${CART_FIELDS} } userErrors { message } warnings { message } } }`, { cartId, lines });

export const cartLinesUpdate = (cartId: string, lines: { id: string; quantity: number }[]) =>
  mutate("cartLinesUpdate",
    `mutation($cartId: ID!, $lines: [CartLineUpdateInput!]!) { cartLinesUpdate(cartId: $cartId, lines: $lines) {
       cart { ${CART_FIELDS} } userErrors { message } warnings { message } } }`, { cartId, lines });

export const cartLinesRemove = (cartId: string, lineIds: string[]) =>
  mutate("cartLinesRemove",
    `mutation($cartId: ID!, $lineIds: [ID!]!) { cartLinesRemove(cartId: $cartId, lineIds: $lineIds) {
       cart { ${CART_FIELDS} } userErrors { message } warnings { message } } }`, { cartId, lineIds });
