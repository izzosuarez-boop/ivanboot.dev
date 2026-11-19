"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { updateLine } from "../cart-client";

export function LineControls({ lineId, quantity, max }: { lineId: string; quantity: number; max: number }) {
  const [pending, start] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const set = (q: number) =>
    start(async () => {
      const r = await updateLine(lineId, q);
      setError(r.ok ? (r.message ?? null) : (r.message ?? "Something went wrong."));
      router.refresh(); // re-render the cart from Shopify (quantities, totals, header count)
    });

  return (
    <div className={pending ? "opacity-50" : ""}>
      <div className="flex items-center gap-4">
        <div className="flex items-center rounded-full border border-sand-2" aria-label="Quantity">
          <button type="button" disabled={pending} onClick={() => set(quantity - 1)} className="px-3 py-1.5 text-clay-muted hover:text-clay" aria-label="Decrease quantity">−</button>
          <span className="w-5 text-center text-sm tabular-nums">{quantity}</span>
          <button type="button" disabled={pending || quantity >= max} onClick={() => set(quantity + 1)} className="px-3 py-1.5 text-clay-muted hover:text-clay disabled:opacity-30" aria-label="Increase quantity">+</button>
        </div>
        <button type="button" disabled={pending} onClick={() => set(0)} className="text-xs text-clay-muted underline underline-offset-2 hover:text-clay">
          Remove
        </button>
      </div>
      {error && <p className="mt-1 text-xs text-[#9a5b3c]" role="status">{error}</p>}
    </div>
  );
}
