import { clsx } from "clsx";

export function KpiTile({
  label,
  value,
  tone = "neutral",
  live = false,
}: {
  label: string;
  value: string | number;
  tone?: "neutral" | "good" | "warn" | "bad";
  live?: boolean;
}) {
  const toneClass = {
    neutral: "text-slate-100",
    good: "text-accent-green",
    warn: "text-accent-amber",
    bad: "text-accent-red",
  }[tone];

  return (
    <div className="rounded-lg border border-surface-border bg-surface-raised p-4">
      <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-slate-400">
        {live && <span className="h-2 w-2 animate-pulse-soft rounded-full bg-accent-cyan" />}
        {label}
      </div>
      <div className={clsx("mt-2 font-mono text-2xl font-semibold", toneClass)}>{value}</div>
    </div>
  );
}
