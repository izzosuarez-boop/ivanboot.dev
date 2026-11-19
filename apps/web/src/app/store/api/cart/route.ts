import { NextResponse, type NextRequest } from "next/server";
import { CART_COOKIE, cartCreate, cartLinesAdd, cartLinesRemove, cartLinesUpdate } from "@/lib/cart";

// Cart mutations go through a Route Handler (not a Server Action) so the response is
// complete before it is sent and the Set-Cookie header is guaranteed to reach the browser.
// Measured 2026-11-19: from a Server Action the cookie set after awaiting Shopify never
// made it into the response headers, so every "add" silently started a new cart.
// Reached as tienda.ivanboot.dev/api/cart (proxy rewrite) or /store/api/cart locally.

export type CartActionResult = { ok: boolean; totalQuantity?: number; message?: string };

const VARIANT_GID = /^gid:\/\/shopify\/ProductVariant\/\d+$/;
const LINE_GID = /^gid:\/\/shopify\/CartLine\/[^\s]{1,250}$/;
const MAX_QTY = 10;

function json(body: CartActionResult, status = 200, cartId?: string) {
  const res = NextResponse.json(body, { status });
  if (cartId) {
    res.cookies.set(CART_COOKIE, cartId, {
      httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax", path: "/", maxAge: 60 * 60 * 24 * 14,
    });
  }
  return res;
}

export async function POST(req: NextRequest) {
  // CSRF: JSON only, and the browser's Origin must be this same host
  const origin = req.headers.get("origin");
  if (!req.headers.get("content-type")?.startsWith("application/json") || (origin && new URL(origin).host !== req.headers.get("host"))) {
    return json({ ok: false, message: "Forbidden" }, 403);
  }
  let body: { action?: string; variantId?: string; lineId?: string; quantity?: number };
  try {
    body = await req.json();
  } catch {
    return json({ ok: false, message: "Bad request" }, 400);
  }
  const quantity = body.quantity ?? 1;
  const cartId = req.cookies.get(CART_COOKIE)?.value;

  try {
    if (body.action === "add") {
      if (!body.variantId || !VARIANT_GID.test(body.variantId) || !Number.isInteger(quantity) || quantity < 1 || quantity > MAX_QTY) {
        return json({ ok: false, message: "Invalid product." }, 400);
      }
      const lines = [{ merchandiseId: body.variantId, quantity }];
      let res = cartId ? await cartLinesAdd(cartId, lines) : null;
      if (!res?.cart) res = await cartCreate(lines); // no cart yet, or it expired / became an order
      if (!res.cart) return json({ ok: false, message: res.problems[0] ?? "Could not add to bag." }, 422);
      return json({ ok: true, totalQuantity: res.cart.totalQuantity, message: res.problems[0] }, 200, res.cart.id);
    }

    if (body.action === "update") {
      if (!body.lineId || !LINE_GID.test(body.lineId) || !Number.isInteger(quantity) || quantity < 0 || quantity > MAX_QTY) {
        return json({ ok: false, message: "Invalid quantity." }, 400);
      }
      if (!cartId) return json({ ok: false, message: "Your bag has expired." }, 410);
      const res = quantity === 0
        ? await cartLinesRemove(cartId, [body.lineId])
        : await cartLinesUpdate(cartId, [{ id: body.lineId, quantity }]);
      return json({ ok: Boolean(res.cart), totalQuantity: res.cart?.totalQuantity, message: res.problems[0] });
    }

    return json({ ok: false, message: "Unknown action" }, 400);
  } catch {
    return json({ ok: false, message: "The store is not responding. Please try again." }, 502);
  }
}
