import Link from "next/link";
import { getCart } from "@/lib/cart";
import { storeHref } from "@/lib/site";

export async function BagLink() {
  const cart = await getCart();
  const n = cart?.totalQuantity ?? 0;
  return (
    <Link href={storeHref("/cart")} className="relative hover:text-clay" aria-label={`Bag, ${n} item${n === 1 ? "" : "s"}`}>
      Bag
      <span className={`ml-1.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1 text-[11px] tabular-nums ${n ? "bg-clay text-sand" : "bg-sand-2 text-clay-muted"}`}>
        {n}
      </span>
    </Link>
  );
}

export function BagLinkFallback() {
  return <span className="text-clay-muted">Bag</span>;
}
