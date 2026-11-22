import { createHash, timingSafeEqual } from "node:crypto";
import { revalidateTag } from "next/cache";

// Called by the API (apps/api/app/web_cache.py) when Shopify stock changes, so the store shows the new
// stock — or "sold out" — at once instead of after the cache expires. The secret is derived from the
// Shopify client secret that both containers already read from the same .env.
const ALLOWED = new Set(["products"]);

function expectedSecret(): string | null {
  const base = process.env.SHOPIFY_CLIENT_SECRET;
  return base ? createHash("sha256").update(`ardea-revalidate:${base}`).digest("hex") : null;
}

export async function POST(request: Request) {
  const expected = expectedSecret();
  const given = request.headers.get("x-revalidate-secret") ?? "";
  if (!expected || given.length !== expected.length || !timingSafeEqual(Buffer.from(given), Buffer.from(expected))) {
    return Response.json({ ok: false }, { status: 401 });
  }
  const body = (await request.json().catch(() => ({}))) as { tags?: unknown };
  const tags = (Array.isArray(body.tags) ? body.tags : ["products"]).filter(
    (t): t is string => typeof t === "string" && ALLOWED.has(t),
  );
  for (const tag of tags) revalidateTag(tag, { expire: 0 }); // drop now: the next visitor gets fresh stock
  return Response.json({ ok: true, revalidated: tags });
}
