"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/signals", label: "Signals" },
  { href: "/models", label: "Models" },
  { href: "/calibration", label: "Calibration" },
  { href: "/regimes", label: "Regimes" },
  { href: "/replay", label: "Replay" },
  { href: "/risk", label: "Risk" },
  { href: "/notifications", label: "Notifications" },
  { href: "/drift", label: "Drift" },
  { href: "/infrastructure", label: "Infrastructure" },
  { href: "/audit", label: "Audit" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-surface-border bg-surface-raised/60 p-4">
      <div className="mb-8">
        <p className="text-xs uppercase tracking-[0.2em] text-accent-cyan">MoneyMaker</p>
        <h1 className="text-lg font-semibold text-white">Quant Control</h1>
      </div>
      <nav className="flex flex-1 flex-col gap-1">
        {NAV.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-accent-cyan/10 text-accent-cyan"
                  : "text-slate-400 hover:bg-surface-border/50 hover:text-slate-100",
              )}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
      <Link
        href="/login"
        className="mb-2 block text-xs text-slate-500 hover:text-accent-cyan"
      >
        Sign in / auth setup
      </Link>
      <p className="text-[10px] text-slate-500">Internal ops · Not user-facing</p>
    </aside>
  );
}
