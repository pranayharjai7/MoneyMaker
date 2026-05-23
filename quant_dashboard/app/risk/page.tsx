"use client";

import { useCallback } from "react";
import { dashboardApi } from "@/lib/api";
import { useDashboardData } from "@/lib/hooks/useDashboardData";
import { RiskPanel } from "@/risk_intelligence/RiskPanel";

export default function RiskPage() {
  const loader = useCallback(() => dashboardApi.risk(), []);
  const { data, error, loading } = useDashboardData(loader);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-white">Risk Intelligence</h1>
      {loading && <p className="text-slate-500">Loading portfolio risk…</p>}
      {error && <p className="text-accent-red">{error}</p>}
      <RiskPanel data={data} />
    </div>
  );
}
