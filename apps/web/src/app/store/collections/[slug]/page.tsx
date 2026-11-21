import { Suspense } from "react";
import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { categories, categoryMedia, getCategory, NAV_LABELS } from "@/lib/categories";
import { getCollectionProducts, type Product } from "@/lib/shopify";
import { storeHref } from "@/lib/site";
import { ProductCard } from "../../_components/product-card";
import { HowToVideo } from "../../_components/howto-video";

export function generateStaticParams() {
  return categories.map((c) => ({ slug: c.slug }));
}

export async function generateMetadata({ params }: PageProps<"/store/collections/[slug]">): Promise<Metadata> {
  const c = getCategory((await params).slug);
  return c ? { title: c.title, description: c.tagline } : {};
}

async function ProductsBlock({ handle, chooser }: { handle: string; chooser: { need: string; handle: string }[] }) {
  await connection();
  let products: Product[] = [];
  try {
    products = await getCollectionProducts(handle);
  } catch {
    return <p className="text-clay-muted">Products are taking a moment to load. Please refresh.</p>;
  }
  const byHandle = new Map(products.map((p) => [p.handle, p]));
  return (
    <>
      {chooser.length > 1 && (
        <div className="mb-12 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {chooser.map((c) => {
            const p = byHandle.get(c.handle);
            return p ? (
              <Link key={c.handle} href={storeHref(`/products/${p.handle}`)} className="group flex items-center justify-between gap-3 rounded-2xl border border-sand-2 bg-white/40 px-5 py-4 transition hover:border-clay-muted">
                <span>
                  <span className="block text-xs uppercase tracking-widest text-clay-muted">{c.need}</span>
                  <span className="mt-1 block font-medium">{p.title}</span>
                </span>
                <span className="text-sage-dark transition group-hover:translate-x-1">→</span>
              </Link>
            ) : null;
          })}
        </div>
      )}
      <div className="grid grid-cols-2 gap-x-5 gap-y-10 lg:grid-cols-4">
        {products.map((p) => <ProductCard key={p.id} product={p} />)}
      </div>
    </>
  );
}

async function CategoryPage({ params }: { params: PageProps<"/store/collections/[slug]">["params"] }) {
  const { slug } = await params;
  const c = getCategory(slug);
  if (!c) notFound();
  const media = categoryMedia(slug);
  const idx = categories.findIndex((x) => x.slug === slug);
  const prev = categories[idx - 1];
  const next = categories[idx + 1];
  const video = media.video?.sources ?? [];

  return (
    <>
      {/* Hero */}
      <section className="relative overflow-hidden">
        {media.hero ? (
          <div className="relative h-[56vh] min-h-[380px] w-full">
            <Image src={media.hero.url} alt={media.hero.alt} fill priority sizes="100vw" className="object-cover" />
            <div className="absolute inset-0 bg-gradient-to-r from-sand via-sand/80 to-transparent sm:via-sand/55" />
          </div>
        ) : (
          <div className="h-[34vh] min-h-[260px] bg-sand-2/50" />
        )}
        <div className="absolute inset-0 flex items-center">
          <div className="mx-auto w-full max-w-6xl px-4 sm:px-6">
            <div className="max-w-md">
              <p className="rise text-xs uppercase tracking-[0.22em] text-sage-dark">{c.kicker}</p>
              <h1 className="rise rise-1 mt-3 font-serif text-5xl leading-[1.05] sm:text-6xl">{c.title}</h1>
              <p className="rise rise-2 mt-4 text-lg text-clay-muted">{c.tagline}</p>
              <a href="#products" className="rise rise-3 mt-7 inline-block rounded-full bg-clay px-6 py-3 text-sm text-sand transition hover:bg-sage-dark">
                Shop {c.title.toLowerCase()}
              </a>
            </div>
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        {/* Why */}
        <section className="grid gap-10 py-16 md:grid-cols-[1fr_1.4fr] md:gap-16">
          <div>
            <h2 className="font-serif text-3xl">Why {c.title.toLowerCase()}?</h2>
            <p className="mt-4 leading-relaxed text-clay-muted">{c.intro}</p>
          </div>
          <ul className="grid gap-4 sm:grid-cols-3 md:grid-cols-1 lg:grid-cols-3">
            {c.benefits.map((b) => (
              <li key={b.title} className="rounded-2xl bg-sand-2/50 p-5">
                <p className="font-medium">{b.title}</p>
                <p className="mt-1.5 text-sm leading-relaxed text-clay-muted">{b.text}</p>
              </li>
            ))}
          </ul>
        </section>

        {/* How to */}
        <section id="how-to" className="scroll-mt-24 border-t border-sand-2 py-16">
          <h2 className="font-serif text-3xl">How to use</h2>
          <div className={`mt-8 grid gap-10 ${video.length ? "lg:grid-cols-[1fr_1.35fr]" : ""}`}>
            <ol className="space-y-5">
              {c.howTo.map((s, i) => (
                <li key={s.title} className="flex gap-4">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-sage font-serif text-sage-dark">{i + 1}</span>
                  <div>
                    <p className="font-medium">{s.title}</p>
                    <p className="mt-1 text-sm leading-relaxed text-clay-muted">{s.text}</p>
                  </div>
                </li>
              ))}
              {c.tip && <li className="rounded-2xl border border-dashed border-sage/60 p-4 text-sm text-clay-muted"><b className="text-clay">Tip · </b>{c.tip}</li>}
            </ol>
            {video.length > 0 && (
              <figure>
                <HowToVideo sources={video} poster={media.poster?.url} label={`How to use ${c.title.toLowerCase()}`} />
                <figcaption className="mt-2 text-xs text-clay-muted">15-second guide · plays when it&apos;s fully in view</figcaption>
              </figure>
            )}
          </div>
        </section>

        {/* Products */}
        <section id="products" className="scroll-mt-24 border-t border-sand-2 py-16">
          <h2 className="font-serif text-3xl">Choose yours</h2>
          <div className="mt-8">
            <Suspense fallback={<div className="h-64 animate-pulse rounded-3xl bg-sand-2/50" />}>
              <ProductsBlock handle={c.collection} chooser={c.chooser} />
            </Suspense>
          </div>
        </section>

        {/* Routine navigation */}
        <nav className="flex items-center justify-between gap-4 border-t border-sand-2 py-10 text-sm" aria-label="Routine steps">
          {prev ? (
            <Link href={storeHref(`/collections/${prev.slug}`)} className="text-clay-muted hover:text-clay">← {NAV_LABELS[prev.slug]}: {prev.title}</Link>
          ) : <span />}
          {next ? (
            <Link href={storeHref(`/collections/${next.slug}`)} className="text-right text-clay-muted hover:text-clay">{NAV_LABELS[next.slug]}: {next.title} →</Link>
          ) : <span />}
        </nav>
      </div>
    </>
  );
}

export default function Page({ params }: PageProps<"/store/collections/[slug]">) {
  return (
    <Suspense fallback={<div className="h-[56vh] animate-pulse bg-sand-2/50" />}>
      <CategoryPage params={params} />
    </Suspense>
  );
}
