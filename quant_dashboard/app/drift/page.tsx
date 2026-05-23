"use client";

import { useCallback } from "react";
import { dashboardApi } from "@/lib/api";
import { useDashboardData } from "@/lib/hooks/useDashboardData";
import { DriftPanel } from "@/drift_visualization/DriftPanel";

export default function DriftPage() {
  const loader = useCallback(() => dashboardApi.drift(), []);
  const { data, error, loading } = useDashboardData(loader);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-white">Drift Visualization</h1>
      {loading && <p className="text-slate-500">Monitoring model degradation…</p>}
      {error && <p className="text-accent-red">{error}</p>}
      <DriftPanel data={data} />
    </div>
  );
}
