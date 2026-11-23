import type { Viewport } from "next";
import { PortfolioShell } from "./_components/portfolio-shell";

// The portfolio is dark already. Saying so (<meta name="color-scheme" content="dark">) keeps browsers with a
// forced dark mode (Chromium's auto dark, Android WebView's algorithmic darkening, Mi Browser) from repainting
// it: Mi Browser turned the hub circle's dark SVG fills light grey (2026-11-23, PLAYBOOK E30). The store is
// light and keeps its own layout.
export const viewport: Viewport = { colorScheme: "dark", themeColor: "#0b0d10" };

export default function PortfolioLayout({ children }: { children: React.ReactNode }) {
  return <PortfolioShell>{children}</PortfolioShell>;
}
