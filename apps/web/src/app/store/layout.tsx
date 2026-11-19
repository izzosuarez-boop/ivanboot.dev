import type { Metadata } from "next";
import Link from "next/link";
import { site, storeHref } from "@/lib/site";

export const metadata: Metadata = {
  title: { default: "Ardea Skin — Skincare that explains itself", template: "%s · Ardea Skin" },
  description: "A demo skincare store: headless Shopify, an AI skin advisor and automated customer care.",
};

export default function StoreLayout({ children }: LayoutProps<"/store">) {
  return (
    <div className="flex flex-1 flex-col bg-sand text-clay">
      <div className="bg-clay px-4 py-2 text-center text-xs text-sand/90">
        Portfolio demo — Ardea Skin is a fictional brand built by{" "}
        <a href={`https://${site.domain}`} className="underline underline-offset-2 hover:text-sand">{site.domain}</a>. No real orders are processed.
      </div>
      <header className="sticky top-0 z-20 border-b border-sand-2 bg-sand/85 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
          <Link href={storeHref("/")} className="font-serif text-xl tracking-[0.18em]">ARDEA SKIN</Link>
          <nav className="flex items-center gap-5 text-sm text-clay-muted">
            <Link href={storeHref("/#shop")} className="hover:text-clay">Shop</Link>
            <Link href={storeHref("/#routine")} className="hover:text-clay">Routine</Link>
            <span className="hidden rounded-full border border-sage px-3 py-1 text-xs text-sage-dark sm:inline">AI advisor · soon</span>
          </nav>
        </div>
      </header>
      <main className="flex-1">{children}</main>
      <footer className="border-t border-sand-2">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-8 text-xs text-clay-muted sm:flex-row sm:justify-between sm:px-6">
          <span>Ardea Skin · fictional brand for demonstration</span>
          <span>Built with Shopify Storefront API, Next.js and Claude — <a href={`https://${site.domain}`} className="underline underline-offset-2">see how</a></span>
        </div>
      </footer>
    </div>
  );
}
