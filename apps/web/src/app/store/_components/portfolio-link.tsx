"use client";

import { useSyncExternalStore } from "react";

const noop = () => () => {};
// The store runs on one subdomain per version of the portfolio (2026-11-25: the Upwork site and the Workana site
// each have their own), so its links back go to the portfolio of the domain it was opened on, never the other one.
const portfolioHost = () => window.location.hostname.replace(/^tienda\./, "");

export function PortfolioLink({ label, className }: { label?: string; className?: string }) {
  const host = useSyncExternalStore(noop, portfolioHost, () => "");
  const real = host.includes(".");                     // localhost: the portfolio is at / on the same server
  return (
    <a href={real ? `https://${host}` : "/"} className={className}>
      {label ?? (real ? host : "my portfolio")}
    </a>
  );
}
