"use client";

import { useCallback } from "react";
import { dashboardApi } from "@/lib/api";
import { useDashboardData } from "@/lib/hooks/useDashboardData";
import { InfraPanel } from "@/infra_observability/InfraPanel";

export default function InfrastructurePage() {
  const loader = useCallback(() => dashboardApi.infrastructure(), []);
  const { data, error, loading } = useDashboardData(loader);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-white">Infrastructure & Observability</h1>
      {loading && <p className="text-slate-500">Checking system health…</p>}
      {error && <p className="text-accent-red">{error}</p>}
      <InfraPanel data={data} />
    </div>
  );
}
