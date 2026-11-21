import { Suspense } from "react";
import Image from "next/image";
import Link from "next/link";
import { connection } from "next/server";
import { categories, categoryMedia, type Category } from "@/lib/categories";
import { getProducts } from "@/lib/shopify";
import { storeHref } from "@/lib/site";
import { BrandVideo } from "./_components/brand-video";
import { ProductVisual } from "./_components/product-visual";

// Homepage: one representative product per routine step, no prices (2026-11-20 request) —
// the full product list lives on each category page.
const featuredHandle = (c: Category) => c.video?.reference ?? c.chooser[0].handle;

async function FeaturedImage({ category }: { category: Category }) {
  await connection();
  const products = await getProducts().catch(() => []);
  const p = products.find((x) => x.handle === featuredHandle(category));
  if (p?.featuredImage) {
    return (
      <Image
        src={p.featuredImage.url}
        alt={p.featuredImage.altText ?? p.title}
        fill
        sizes="(min-width: 768px) 45vw, 100vw"
        className="object-cover transition duration-700 group-hover:scale-[1.03]"
      />
    );
  }
  return <ProductVisual type={category.title} step={category.step} title={category.title} />;
}

function StepSection({ category, index }: { category: Category; index: number }) {
  const href = storeHref(`/collections/${category.slug}`);
  const flip = index % 2 === 1;
  return (
    <section aria-labelledby={`step-${category.slug}`} className="grid items-center gap-8 md:grid-cols-2 md:gap-16">
      <Link href={href} className={`group relative block aspect-square overflow-hidden rounded-3xl bg-sand-2 ${flip ? "md:order-2" : ""}`} aria-label={`${category.title}: see the range`}>
        <Suspense fallback={<div className="h-full w-full animate-pulse bg-sand-2" />}>
          <FeaturedImage category={category} />
        </Suspense>
      </Link>
      <div>
        <p className="text-xs uppercase tracking-[0.22em] text-sage-dark">{category.kicker}</p>
        <h2 id={`step-${category.slug}`} className="mt-3 font-serif text-4xl leading-tight sm:text-5xl">{category.title}</h2>
        <p className="mt-3 text-lg text-clay">{category.tagline}</p>
        <p className="mt-4 leading-relaxed text-clay-muted">{category.intro}</p>
        <ul className="mt-6 flex flex-wrap gap-2">
          {category.benefits.map((b) => (
            <li key={b.title} className="rounded-full border border-sand-2 px-3.5 py-1.5 text-sm">{b.title}</li>
          ))}
        </ul>
        <div className="mt-8 flex flex-wrap items-center gap-5">
          <Link href={href} className="rounded-full bg-clay px-6 py-3 text-sm text-sand transition hover:bg-sage-dark">
            Explore {category.title.toLowerCase()}
          </Link>
          <Link href={`${href}#how-to`} className="text-sm text-sage-dark underline-offset-4 hover:text-clay hover:underline">
            How to use →
          </Link>
        </div>
      </div>
    </section>
  );
}

export default function StoreHome() {
  const brand = categoryMedia("home");
  return (
    <>
      <section className="relative isolate flex min-h-[78vh] items-end overflow-hidden">
        {brand.video ? (
          <BrandVideo sources={brand.video.sources} poster={brand.poster?.url} />
        ) : (
          <div className="absolute inset-0 bg-sand-2" />
        )}
        <div aria-hidden className="absolute inset-0 bg-gradient-to-t from-sand via-sand/45 to-transparent" />
        <div className="relative mx-auto w-full max-w-6xl px-4 pb-14 sm:px-6 sm:pb-20">
          <p className="rise text-sm uppercase tracking-[0.2em] text-sage-dark">Fragrance-free skincare</p>
          <h1 className="rise rise-1 mt-4 max-w-2xl font-serif text-5xl leading-[1.05] sm:text-7xl">Skincare that explains itself.</h1>
          <p className="rise rise-2 mt-5 max-w-lg text-lg text-clay-muted">
            Three simple steps — morning, afternoon, evening. Each one explains what it does and how to use it.
          </p>
          <a href="#shop" className="rise rise-3 mt-8 inline-block rounded-full bg-clay px-6 py-3 text-sm text-sand transition hover:bg-sage-dark">
            Discover the routine
          </a>
        </div>
      </section>

      <div id="shop" className="mx-auto max-w-6xl scroll-mt-28 space-y-24 px-4 py-20 sm:px-6 sm:py-28">
        {categories.map((c, i) => <StepSection key={c.slug} category={c} index={i} />)}
      </div>
    </>
  );
}
