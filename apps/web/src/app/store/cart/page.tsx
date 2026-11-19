import { Suspense } from "react";
import Link from "next/link";
import Image from "next/image";
import type { Metadata } from "next";
import { getCart } from "@/lib/cart";
import { formatMoney } from "@/lib/shopify";
import { storeHref } from "@/lib/site";
import { LineControls } from "./line-controls";

export const metadata: Metadata = { title: "Your bag", robots: { index: false } };

// Shown when the dev store's password page sits in front of checkout (Shopify dev stores).
const STORE_PASSWORD = process.env.NEXT_PUBLIC_STORE_PASSWORD ?? "";

async function CartContents() {
  const cart = await getCart();

  if (!cart || cart.lines.length === 0) {
    return (
      <div className="rounded-3xl bg-sand-2/40 px-6 py-16 text-center">
        <p className="font-serif text-2xl">Your bag is empty.</p>
        <p className="mt-2 text-sm text-clay-muted">Start with a cleanser, or let the routine guide you.</p>
        <Link href={storeHref("/#shop")} className="mt-6 inline-block rounded-full bg-clay px-6 py-3 text-sm text-sand hover:bg-sage-dark">
          Shop the routine
        </Link>
      </div>
    );
  }

  return (
    <div className="grid gap-10 lg:grid-cols-[1fr_360px]">
      <ul className="divide-y divide-sand-2 border-y border-sand-2">
        {cart.lines.map((line) => {
          const m = line.merchandise;
          const option = m.selectedOptions.find((o) => o.value !== "Default Title");
          return (
            <li key={line.id} className="flex gap-4 py-5">
              <Link href={storeHref(`/products/${m.product.handle}`)} className="relative h-24 w-24 shrink-0 overflow-hidden rounded-2xl bg-sand-2">
                {m.image && <Image src={m.image.url} alt={m.image.altText ?? m.product.title} fill sizes="96px" className="object-cover" />}
              </Link>
              <div className="flex flex-1 flex-col justify-between gap-2 sm:flex-row sm:items-start">
                <div>
                  <Link href={storeHref(`/products/${m.product.handle}`)} className="font-medium hover:underline">{m.product.title}</Link>
                  {option && <p className="text-xs text-clay-muted">{option.name}: {option.value}</p>}
                  <p className="mt-1 text-sm text-clay-muted">{formatMoney(m.price)} each</p>
                  <div className="mt-3">
                    <LineControls lineId={line.id} quantity={line.quantity} max={Math.min(10, m.quantityAvailable ?? 10)} />
                  </div>
                </div>
                <p className="text-sm sm:text-right">{formatMoney(line.cost.totalAmount)}</p>
              </div>
            </li>
          );
        })}
      </ul>

      <aside className="h-fit rounded-3xl bg-sand-2/50 p-6 lg:sticky lg:top-24">
        <h2 className="font-serif text-xl">Summary</h2>
        <dl className="mt-4 space-y-2 text-sm">
          <div className="flex justify-between"><dt className="text-clay-muted">Subtotal ({cart.totalQuantity} items)</dt><dd>{formatMoney(cart.cost.subtotalAmount)}</dd></div>
          <div className="flex justify-between"><dt className="text-clay-muted">Shipping & taxes</dt><dd className="text-clay-muted">at checkout</dd></div>
        </dl>
        <a href={cart.checkoutUrl} className="mt-6 block rounded-full bg-clay px-6 py-3.5 text-center text-sm text-sand transition hover:bg-sage-dark">
          Checkout
        </a>
        <div className="mt-5 rounded-2xl border border-dashed border-sage/60 p-4 text-xs leading-relaxed text-clay-muted">
          <p className="font-medium text-clay">Try the full checkout — it&apos;s a test store.</p>
          <p className="mt-1">No real payment is taken. Use any name and address, and card number <b className="text-clay">1</b> with any future date and CVV.</p>
          {STORE_PASSWORD && (
            <p className="mt-1">If Shopify asks for the store password, enter <b className="text-clay">{STORE_PASSWORD}</b>.</p>
          )}
        </div>
      </aside>
    </div>
  );
}

function CartSkeleton() {
  return <div className="h-64 animate-pulse rounded-3xl bg-sand-2/60" />;
}

export default function CartPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 pb-24 pt-10 sm:px-6">
      <h1 className="font-serif text-4xl">Your bag</h1>
      <div className="mt-8">
        <Suspense fallback={<CartSkeleton />}>
          <CartContents />
        </Suspense>
      </div>
    </div>
  );
}
