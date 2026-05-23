"use client";

import { useCallback } from "react";
import { dashboardApi } from "@/lib/api";
import { useDashboardData } from "@/lib/hooks/useDashboardData";
import { ReplayPanel } from "@/replay_visualization/ReplayPanel";

export default function ReplayPage() {
  const loader = useCallback(() => dashboardApi.replay(), []);
  const { data, error, loading } = useDashboardData(loader);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-white">Replay Visualization</h1>
      {loading && <p className="text-slate-500">Loading replay analytics…</p>}
      {error && <p className="text-accent-red">{error}</p>}
      <ReplayPanel initialData={data} />
    </div>
  );
}
