import Link from "next/link";
import Image from "next/image";
import { formatMoney, type Product } from "@/lib/shopify";
import { storeHref } from "@/lib/site";
import { ProductVisual } from "./product-visual";

export function stockBadge(p: Pick<Product, "availableForSale" | "totalInventory">) {
  if (!p.availableForSale) return { label: "Sold out", tone: "bg-clay text-sand" };
  if (p.totalInventory !== null && p.totalInventory <= 5) return { label: `Only ${p.totalInventory} left`, tone: "bg-blush text-clay" };
  return null;
}

export function ProductCard({ product }: { product: Product }) {
  const price = product.priceRange.minVariantPrice;
  const compare = product.compareAtPriceRange.maxVariantPrice;
  const onSale = Number(compare.amount) > Number(price.amount);
  const badge = stockBadge(product);
  const multi = product.variants.length > 1;

  return (
    <Link href={storeHref(`/products/${product.handle}`)} className="group block">
      <div className="relative aspect-square overflow-hidden rounded-2xl">
        {product.featuredImage ? (
          <Image
            src={product.featuredImage.url}
            alt={product.featuredImage.altText ?? product.title}
            fill
            sizes="(min-width: 1024px) 25vw, (min-width: 640px) 33vw, 50vw"
            className="object-cover transition duration-500 group-hover:scale-[1.03]"
          />
        ) : (
          <div className="h-full w-full transition duration-500 group-hover:scale-[1.03]">
            <ProductVisual type={product.productType} step={product.routineStep} title={product.title} />
          </div>
        )}
        <div className="absolute left-3 top-3 flex gap-1.5">
          {badge && <span className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${badge.tone}`}>{badge.label}</span>}
          {onSale && <span className="rounded-full bg-sage-dark px-2.5 py-1 text-[11px] font-medium text-sand">Sale</span>}
        </div>
      </div>
      <div className="mt-3 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-[15px] font-medium leading-snug text-clay">{product.title}</h3>
          <p className="mt-0.5 text-xs text-clay-muted">{product.skinTypes.length === 5 ? "All skin types" : product.skinTypes.join(", ")}</p>
        </div>
        <p className="shrink-0 text-sm text-clay">
          {multi && <span className="text-clay-muted">from </span>}
          {formatMoney(price)}
          {onSale && <span className="ml-1.5 text-clay-muted line-through">{formatMoney(compare)}</span>}
        </p>
      </div>
    </Link>
  );
}
