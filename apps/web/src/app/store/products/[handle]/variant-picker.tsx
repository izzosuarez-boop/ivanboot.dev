"use client";

import { useState } from "react";
import type { Variant } from "@/lib/shopify";

function money(amount: string, currency: string) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(Number(amount));
}

export function VariantPicker({ variants }: { variants: Variant[] }) {
  const firstAvailable = variants.find((v) => v.availableForSale) ?? variants[0];
  const [selectedId, setSelectedId] = useState(firstAvailable.id);
  const v = variants.find((x) => x.id === selectedId) ?? firstAvailable;
  const optionName = v.selectedOptions[0]?.name ?? "Size";
  const onSale = v.compareAtPrice && Number(v.compareAtPrice.amount) > Number(v.price.amount);
  const low = v.availableForSale && v.quantityAvailable !== null && v.quantityAvailable <= 5;

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
                onClick={() => setSelectedId(x.id)}
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

      <button
        type="button"
        disabled
        className="mt-6 w-full rounded-full bg-clay px-6 py-3.5 text-sm text-sand opacity-60"
        title="Cart and checkout arrive in the next iteration of the demo"
      >
        {v.availableForSale ? "Add to bag · checkout opens soon" : "Notify me · coming soon"}
      </button>
    </div>
  );
}
