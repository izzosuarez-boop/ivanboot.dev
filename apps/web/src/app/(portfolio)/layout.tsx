import { PortfolioShell } from "./_components/portfolio-shell";

export default function PortfolioLayout({ children }: { children: React.ReactNode }) {
  return <PortfolioShell>{children}</PortfolioShell>;
}
