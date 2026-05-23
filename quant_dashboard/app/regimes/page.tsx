"use client";

import { useCallback } from "react";
import { dashboardApi } from "@/lib/api";
import { useDashboardData } from "@/lib/hooks/useDashboardData";
import { RegimeAnalyticsPanel } from "@/regime_analytics/RegimeAnalyticsPanel";

export default function RegimesPage() {
  const loader = useCallback(() => dashboardApi.regimes(), []);
  const { data, error, loading } = useDashboardData(loader);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-white">Regime Analytics</h1>
      {loading && <p className="text-slate-500">Loading regime intelligence…</p>}
      {error && <p className="text-accent-red">{error}</p>}
      <RegimeAnalyticsPanel data={data} />
    </div>
  );
}
