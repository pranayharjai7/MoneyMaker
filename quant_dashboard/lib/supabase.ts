import { createClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

export const supabase =
  url && anonKey
    ? createClient(url, anonKey, {
        realtime: { params: { eventsPerSecond: 10 } },
      })
    : null;

export function subscribeDashboardMetrics(onUpdate: () => void) {
  if (!supabase) return () => undefined;
  const channel = supabase
    .channel("quant-dashboard-metrics")
    .on(
      "postgres_changes",
      { event: "*", schema: "public", table: "dashboard_metrics" },
      () => onUpdate(),
    )
    .on(
      "postgres_changes",
      { event: "INSERT", schema: "public", table: "signal_audit_log" },
      () => onUpdate(),
    )
    .subscribe();
  return () => {
    supabase.removeChannel(channel);
  };
}
