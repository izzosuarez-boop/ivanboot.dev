import { Suspense } from "react";
import Link from "next/link";
import Image from "next/image";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { getProduct, STEP_LABELS } from "@/lib/shopify";
import { storeHref } from "@/lib/site";
import { ProductVisual } from "../../_components/product-visual";
import { VariantPicker } from "./variant-picker";

const CONCERN_LABELS: Record<string, string> = {
  acne: "Blemishes", pores: "Pores", "dark-spots": "Dark spots", dullness: "Dullness",
  dehydration: "Dehydration", redness: "Redness", aging: "Fine lines", texture: "Texture",
};

async function ProductDetails({ params }: { params: PageProps<"/store/products/[handle]">["params"] }) {
  const { handle } = await params;
  await connection();
  const p = await getProduct(handle);
  if (!p) notFound();

  return (
    <div className="grid gap-10 md:grid-cols-2 md:gap-14">
      <div className="relative aspect-square overflow-hidden rounded-3xl md:sticky md:top-24 md:self-start">
        {p.featuredImage ? (
          <Image src={p.featuredImage.url} alt={p.featuredImage.altText ?? p.title} fill priority sizes="(min-width: 768px) 50vw, 100vw" className="object-cover" />
        ) : (
          <ProductVisual type={p.productType} step={p.routineStep} title={p.title} />
        )}
      </div>

      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-sage-dark">
          Step {p.routineStep} · {STEP_LABELS[p.routineStep]} · {p.usageTime}
        </p>
        <h1 className="mt-3 font-serif text-4xl leading-tight">{p.title}</h1>
        <div className="mt-6">
          <VariantPicker variants={p.variants} />
        </div>

        <div className="prose-sm mt-10 text-clay [&_li]:ml-4 [&_li]:list-disc [&_li]:py-0.5 [&_p]:mb-3" dangerouslySetInnerHTML={{ __html: p.descriptionHtml }} />

        <dl className="mt-8 grid grid-cols-2 gap-4 text-sm">
          <div className="rounded-2xl bg-sand-2/50 p-4">
            <dt className="text-xs uppercase tracking-widest text-clay-muted">Skin type</dt>
            <dd className="mt-1">{p.skinTypes.length === 5 ? "All skin types" : p.skinTypes.map((s) => s[0].toUpperCase() + s.slice(1)).join(", ")}</dd>
          </div>
          <div className="rounded-2xl bg-sand-2/50 p-4">
            <dt className="text-xs uppercase tracking-widest text-clay-muted">Helps with</dt>
            <dd className="mt-1">{p.concerns.map((c) => CONCERN_LABELS[c] ?? c).join(", ")}</dd>
          </div>
          <div className="rounded-2xl bg-sand-2/50 p-4">
            <dt className="text-xs uppercase tracking-widest text-clay-muted">Texture</dt>
            <dd className="mt-1">{p.texture}</dd>
          </div>
          <div className="rounded-2xl bg-sand-2/50 p-4">
            <dt className="text-xs uppercase tracking-widest text-clay-muted">Fragrance</dt>
            <dd className="mt-1">{p.fragranceFree ? "Fragrance-free" : "Contains fragrance"}</dd>
          </div>
        </dl>

        <section className="mt-10 border-t border-sand-2 pt-6">
          <h2 className="font-serif text-xl">Key ingredients</h2>
          <ul className="mt-3 flex flex-wrap gap-2">
            {p.keyIngredients.map((i) => (
              <li key={i} className="rounded-full border border-sand-2 px-3 py-1.5 text-sm">{i}</li>
            ))}
          </ul>
        </section>
        <section className="mt-8 border-t border-sand-2 pt-6">
          <h2 className="font-serif text-xl">How to use</h2>
          <p className="mt-3 text-sm leading-relaxed text-clay-muted">{p.howToUse}</p>
        </section>
        <section className="mt-8 border-t border-sand-2 pt-6">
          <h2 className="font-serif text-xl">Good to know</h2>
          <p className="mt-3 text-sm leading-relaxed text-clay-muted">{p.cautions}</p>
        </section>
      </div>
    </div>
  );
}

function DetailsSkeleton() {
  return (
    <div className="grid gap-10 md:grid-cols-2">
      <div className="aspect-square animate-pulse rounded-3xl bg-sand-2" />
      <div className="space-y-4">
        <div className="h-4 w-1/3 animate-pulse rounded bg-sand-2" />
        <div className="h-10 w-3/4 animate-pulse rounded bg-sand-2" />
        <div className="h-24 animate-pulse rounded bg-sand-2" />
      </div>
    </div>
  );
}

export default function ProductPage({ params }: PageProps<"/store/products/[handle]">) {
  return (
    <div className="mx-auto max-w-6xl px-4 pb-24 pt-8 sm:px-6">
      <Link href={storeHref("/#shop")} className="text-sm text-clay-muted hover:text-clay">← All products</Link>
      <div className="mt-6">
        <Suspense fallback={<DetailsSkeleton />}>
          <ProductDetails params={params} />
        </Suspense>
      </div>
    </div>
  );
}
