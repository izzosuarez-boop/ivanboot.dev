import { storeHref } from "@/lib/site";
import type { CartActionResult } from "./api/cart/route";

export type { CartActionResult };

async function call(payload: Record<string, unknown>): Promise<CartActionResult> {
  try {
    const res = await fetch(storeHref("/api/cart"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return (await res.json()) as CartActionResult;
  } catch {
    return { ok: false, message: "Network error. Please try again." };
  }
}

export const addToCart = (variantId: string, quantity = 1) => call({ action: "add", variantId, quantity });
export const updateLine = (lineId: string, quantity: number) => call({ action: "update", lineId, quantity });
