"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

// Shopify development stores put a password page in front of checkout, and after the
// password Shopify lands the shopper on its own (unused) theme homepage instead of returning
// to checkout. Two mitigations (2026-11-20, seen in a real browser):
//  1. explain the step and the password BEFORE leaving this site;
//  2. the dev store's theme redirects every storefront page back here with ?unlocked=1,
//     so the shopper presses Checkout again and goes straight in.
export function CheckoutButton({ checkoutUrl, password }: { checkoutUrl: string; password: string }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const unlocked = useSearchParams().get("unlocked") === "1";
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (copied) {
      const t = setTimeout(() => setCopied(false), 1800);
      return () => clearTimeout(t);
    }
  }, [copied]);

  if (unlocked || !password) {
    return (
      <>
        {unlocked && (
          <p className="mt-6 rounded-2xl bg-sage/20 px-4 py-3 text-sm text-sage-dark" role="status">
            Store unlocked. Your bag is saved — continue to checkout.
          </p>
        )}
        <a href={checkoutUrl} className="mt-4 block rounded-full bg-clay px-6 py-3.5 text-center text-sm text-sand transition hover:bg-sage-dark">
          Checkout
        </a>
      </>
    );
  }

  return (
    <>
      <button
        type="button"
        onClick={() => dialog.current?.showModal()}
        className="mt-6 block w-full rounded-full bg-clay px-6 py-3.5 text-center text-sm text-sand transition hover:bg-sage-dark"
      >
        Checkout
      </button>

      <dialog
        ref={dialog}
        className="m-auto w-[min(92vw,440px)] rounded-3xl bg-sand p-0 text-clay backdrop:bg-clay/40 backdrop:backdrop-blur-sm"
        onClick={(e) => e.target === dialog.current && dialog.current?.close()}
      >
        <div className="p-6 sm:p-7">
          <p className="text-xs uppercase tracking-[0.2em] text-sage-dark">Test checkout</p>
          <h2 className="mt-2 font-serif text-2xl leading-snug">One quick step before checkout</h2>
          <p className="mt-3 text-sm leading-relaxed text-clay-muted">
            Ardea runs on a Shopify <b className="text-clay">development store</b>, so Shopify may ask for a store password first.
          </p>

          <div className="mt-5 flex items-center justify-between gap-3 rounded-2xl border border-sand-2 bg-white/60 px-4 py-3">
            <div>
              <p className="text-xs text-clay-muted">Store password</p>
              <p className="font-mono text-lg tracking-wider">{password}</p>
            </div>
            <button
              type="button"
              onClick={() => navigator.clipboard?.writeText(password).then(() => setCopied(true))}
              className="rounded-full border border-sand-2 px-3 py-1.5 text-xs hover:border-clay-muted"
            >
              {copied ? "Copied ✓" : "Copy"}
            </button>
          </div>

          <ol className="mt-5 space-y-2 text-sm text-clay-muted">
            <li><b className="text-clay">1.</b> Enter the password if Shopify asks for it.</li>
            <li><b className="text-clay">2.</b> You&apos;ll be brought back to your bag — press <b className="text-clay">Checkout</b> again.</li>
            <li><b className="text-clay">3.</b> Pay with card <b className="text-clay">1</b>, any future date and CVV. Nothing is charged.</li>
          </ol>

          <div className="mt-6 flex gap-3">
            <button type="button" onClick={() => dialog.current?.close()} className="flex-1 rounded-full border border-sand-2 px-4 py-3 text-sm hover:border-clay-muted">
              Back
            </button>
            <a href={checkoutUrl} className="flex-[2] rounded-full bg-clay px-4 py-3 text-center text-sm text-sand hover:bg-sage-dark">
              Continue to checkout
            </a>
          </div>
        </div>
      </dialog>
    </>
  );
}
