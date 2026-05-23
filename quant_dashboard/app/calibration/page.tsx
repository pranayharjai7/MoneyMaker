"use client";

import { useCallback } from "react";
import { dashboardApi } from "@/lib/api";
import { useDashboardData } from "@/lib/hooks/useDashboardData";
import { CalibrationPanel } from "@/calibration_intelligence/CalibrationPanel";

export default function CalibrationPage() {
  const loader = useCallback(() => dashboardApi.calibration(), []);
  const { data, error, loading } = useDashboardData(loader);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-white">Calibration Intelligence</h1>
      {loading && <p className="text-slate-500">Evaluating probability trust…</p>}
      {error && <p className="text-accent-red">{error}</p>}
      <CalibrationPanel data={data} />
    </div>
  );
}
