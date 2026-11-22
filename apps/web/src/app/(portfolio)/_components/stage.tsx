"use client";

import Link from "next/link";
import { useShell, useShown } from "./portfolio-shell";

// Wraps a page's content: enters after the ring has moved (delay), fades out before the ring moves back.
export function Stage({ children, delay = 0, className = "" }: {
  children: React.ReactNode; delay?: number; className?: string;
}) {
  const { leaving } = useShell();
  const shown = useShown(delay);
  return (
    <div
      className={`transition-[opacity,transform] duration-700 ease-out motion-reduce:transition-none ${
        shown && !leaving ? "translate-y-0 opacity-100" : "translate-y-5 opacity-0"
      } ${className}`}
    >
      {children}
    </div>
  );
}

// A link to another section (or the hub) that runs the ring transition instead of a plain page load.
export function GoLink({ to, className, children }: { to: string | null; className?: string; children: React.ReactNode }) {
  const { go } = useShell();
  return (
    <Link
      href={to ? `/${to}` : "/"}
      className={className}
      onClick={(e) => {
        e.preventDefault();
        go(to);
      }}
    >
      {children}
    </Link>
  );
}
