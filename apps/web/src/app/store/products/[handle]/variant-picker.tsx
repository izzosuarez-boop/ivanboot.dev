"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { Variant } from "@/lib/shopify";
import { addToCart, type CartActionResult } from "../../cart-client";
import { storeHref } from "@/lib/site";

function money(amount: string, currency: string) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(Number(amount));
}

export function VariantPicker({ variants }: { variants: Variant[] }) {
  const firstAvailable = variants.find((v) => v.availableForSale) ?? variants[0];
  const [selectedId, setSelectedId] = useState(firstAvailable.id);
  const [qty, setQty] = useState(1);
  const [result, setResult] = useState<CartActionResult | null>(null);
  const [pending, startTransition] = useTransition();
  const router = useRouter();
  const v = variants.find((x) => x.id === selectedId) ?? firstAvailable;
  const optionName = v.selectedOptions[0]?.name ?? "Size";
  const onSale = v.compareAtPrice && Number(v.compareAtPrice.amount) > Number(v.price.amount);
  const low = v.availableForSale && v.quantityAvailable !== null && v.quantityAvailable <= 5;
  const maxQty = Math.min(10, v.quantityAvailable ?? 10);

  return (
    <div>
      <p className="text-2xl">
        {money(v.price.amount, v.price.currencyCode)}
        {onSale && <span className="ml-2 text-base text-clay-muted line-through">{money(v.compareAtPrice!.amount, v.compareAtPrice!.currencyCode)}</span>}
      </p>

      {variants.length > 1 && (
        <fieldset className="mt-6">
          <legend className="text-xs uppercase tracking-widest text-clay-muted">{optionName}</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {variants.map((x) => (
              <button
                key={x.id}
                type="button"
                onClick={() => { setSelectedId(x.id); setQty(1); setResult(null); }}
                aria-pressed={x.id === v.id}
                disabled={!x.availableForSale}
                className={`rounded-full border px-4 py-2 text-sm transition disabled:cursor-not-allowed disabled:opacity-40 ${
                  x.id === v.id ? "border-clay bg-clay text-sand" : "border-sand-2 hover:border-clay-muted"
                }`}
              >
                {x.selectedOptions[0]?.value ?? x.title}
              </button>
            ))}
          </div>
        </fieldset>
      )}

      <p className="mt-5 text-sm" aria-live="polite">
        {!v.availableForSale ? (
          <span className="text-clay">Sold out — back soon.</span>
        ) : low ? (
          <span className="text-[#9a5b3c]">Only {v.quantityAvailable} left in stock.</span>
        ) : (
          <span className="text-sage-dark">In stock, ships in 1–2 days.</span>
        )}
      </p>

      {v.availableForSale && (
        <div className="mt-6 flex gap-3">
          <div className="flex items-center rounded-full border border-sand-2" aria-label="Quantity">
            <button type="button" onClick={() => setQty((q) => Math.max(1, q - 1))} className="px-4 py-3 text-clay-muted hover:text-clay" aria-label="Decrease quantity">−</button>
            <span className="w-6 text-center text-sm tabular-nums">{qty}</span>
            <button
              type="button"
              onClick={() => setQty((q) => Math.min(maxQty, q + 1))}
              disabled={qty >= maxQty}
              className="px-4 py-3 text-clay-muted hover:text-clay disabled:opacity-30"
              aria-label="Increase quantity"
            >+</button>
          </div>
          <button
            type="button"
            disabled={pending}
            onClick={() =>
              startTransition(async () => {
                const r = await addToCart(v.id, qty);
                setResult(r);
                if (r.ok) router.refresh(); // updates the bag counter in the header
              })
            }
            className="flex-1 rounded-full bg-clay px-6 py-3.5 text-sm text-sand transition hover:bg-sage-dark disabled:opacity-60"
          >
            {pending ? "Adding…" : "Add to bag"}
          </button>
        </div>
      )}

      {result && (
        <p className={`mt-3 text-sm ${result.ok ? "text-sage-dark" : "text-[#9a5b3c]"}`} role="status">
          {result.ok ? (
            <>
              Added to your bag.{" "}
              <Link href={storeHref("/cart")} className="underline underline-offset-2">View bag ({result.totalQuantity})</Link>
              {result.message && <span className="block text-clay-muted">{result.message}</span>}
            </>
          ) : (
            result.message
          )}
        </p>
      )}
    </div>
  );
}
