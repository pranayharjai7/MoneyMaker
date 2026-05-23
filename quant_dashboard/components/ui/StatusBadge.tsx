import { clsx } from "clsx";

export function StatusBadge({ status }: { status: string }) {
  const normalized = status.toUpperCase();
  const tone =
    normalized === "HEALTHY" || normalized === "OK"
      ? "bg-emerald-500/15 text-emerald-300"
      : normalized === "DEGRADED" || normalized === "WARMING_UP"
        ? "bg-amber-500/15 text-amber-300"
        : "bg-rose-500/15 text-rose-300";

  return (
    <span className={clsx("rounded-full px-2 py-0.5 text-xs font-medium", tone)}>{normalized}</span>
  );
}
