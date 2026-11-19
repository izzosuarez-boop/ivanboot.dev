import { Suspense } from "react";
import { connection } from "next/server";
import { getProducts, STEP_LABELS, type Product } from "@/lib/shopify";
import { ProductCard } from "./_components/product-card";

const STEP_NOTES: Record<number, string> = {
  1: "Start clean, morning and night.",
  2: "Rebalance and smooth.",
  3: "Targeted serums for what your skin needs.",
  4: "Lock in hydration.",
  5: "Every morning, the last step.",
  6: "A calming ritual, 2–3 evenings a week.",
};

async function Catalog() {
  await connection(); // live catalog: rendered per request, cached for minutes in lib/shopify
  let products: Product[];
  try {
    products = await getProducts();
  } catch {
    return <p className="py-16 text-center text-clay-muted">The catalog is taking a break. Please try again in a moment.</p>;
  }
  const steps = [...new Set(products.map((p) => p.routineStep))].sort();

  return (
    <div className="space-y-16">
      {steps.map((step) => (
        <section key={step} aria-labelledby={`step-${step}`}>
          <div className="flex items-baseline justify-between gap-4 border-b border-sand-2 pb-3">
            <h2 id={`step-${step}`} className="font-serif text-2xl">
              <span className="mr-3 text-base text-sage-dark">{String(step).padStart(2, "0")}</span>
              {STEP_LABELS[step] ?? "More"}
            </h2>
            <p className="hidden text-sm text-clay-muted sm:block">{STEP_NOTES[step]}</p>
          </div>
          <div className="mt-6 grid grid-cols-2 gap-x-5 gap-y-10 lg:grid-cols-4">
            {products.filter((p) => p.routineStep === step).map((p) => <ProductCard key={p.id} product={p} />)}
          </div>
        </section>
      ))}
    </div>
  );
}

function CatalogSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-x-5 gap-y-10 lg:grid-cols-4">
      {Array.from({ length: 8 }, (_, i) => (
        <div key={i}>
          <div className="aspect-square animate-pulse rounded-2xl bg-sand-2" />
          <div className="mt-3 h-4 w-3/4 animate-pulse rounded bg-sand-2" />
        </div>
      ))}
    </div>
  );
}

export default function StoreHome() {
  return (
    <>
      <section className="mx-auto grid max-w-6xl gap-10 px-4 pb-16 pt-14 sm:px-6 md:grid-cols-[1.2fr_1fr] md:items-end">
        <div>
          <p className="rise text-sm uppercase tracking-[0.2em] text-sage-dark">Fragrance-free skincare</p>
          <h1 className="rise rise-1 mt-4 font-serif text-5xl leading-[1.05] sm:text-6xl">Skincare that explains itself.</h1>
          <p className="rise rise-2 mt-6 max-w-lg text-lg text-clay-muted">
            Thirteen essentials, one simple routine. Tell our skin advisor about your skin and it will build
            your routine — and your bag — in a minute.
          </p>
          <a href="#shop" className="rise rise-3 mt-8 inline-block rounded-full bg-clay px-6 py-3 text-sm text-sand transition hover:bg-sage-dark">
            Shop the routine
          </a>
        </div>
        <ol id="routine" className="rise rise-2 grid grid-cols-3 gap-3 text-center text-xs text-clay-muted">
          {[1, 2, 3, 4, 5, 6].map((s) => (
            <li key={s} className="rounded-2xl border border-sand-2 bg-sand-2/40 px-2 py-4">
              <span className="block font-serif text-2xl text-clay">{s}</span>
              {STEP_LABELS[s]}
            </li>
          ))}
        </ol>
      </section>

      <div id="shop" className="mx-auto max-w-6xl scroll-mt-24 px-4 pb-24 sm:px-6">
        <Suspense fallback={<CatalogSkeleton />}>
          <Catalog />
        </Suspense>
      </div>
    </>
  );
}
