"use client";

import { useCallback } from "react";
import { dashboardApi } from "@/lib/api";
import { useDashboardData } from "@/lib/hooks/useDashboardData";
import { ModelIntelligencePanel } from "@/model_intelligence/ModelIntelligencePanel";

export default function ModelsPage() {
  const loader = useCallback(() => dashboardApi.models(), []);
  const { data, error, loading } = useDashboardData(loader);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-white">Model Intelligence</h1>
      {loading && <p className="text-slate-500">Loading model analytics…</p>}
      {error && <p className="text-accent-red">{error}</p>}
      <ModelIntelligencePanel data={data} />
    </div>
  );
}
