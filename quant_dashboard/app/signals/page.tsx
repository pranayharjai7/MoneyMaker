"use client";

import { useCallback } from "react";
import { dashboardApi } from "@/lib/api";
import { useDashboardData } from "@/lib/hooks/useDashboardData";
import { SignalMonitoringPanel } from "@/signal_monitoring/SignalMonitoringPanel";

export default function SignalsPage() {
  const loader = useCallback(() => dashboardApi.signals(), []);
  const { data, error, loading } = useDashboardData(loader);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-white">Live Signal Monitoring</h1>
      {loading && <p className="text-slate-500">Streaming signals…</p>}
      {error && <p className="text-accent-red">{error}</p>}
      <SignalMonitoringPanel data={data} />
    </div>
  );
}
