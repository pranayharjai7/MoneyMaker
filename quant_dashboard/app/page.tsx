"use client";

import { useCallback } from "react";
import { KpiTile } from "@/components/ui/KpiTile";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Card } from "@/components/ui/Card";
import { dashboardApi } from "@/lib/api";
import { useDashboardData } from "@/lib/hooks/useDashboardData";
import { SignalMonitoringPanel } from "@/signal_monitoring/SignalMonitoringPanel";
import { DriftPanel } from "@/drift_visualization/DriftPanel";

export default function OverviewPage() {
  const loader = useCallback(() => dashboardApi.overview(), []);
  const { data, error, loading } = useDashboardData(loader);

  if (loading && !data) {
    return <p className="text-slate-400">Loading operational intelligence…</p>;
  }
  if (error) {
    return <p className="text-accent-red">{error}</p>;
  }

  const kpis = data?.kpis;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-white">Quant Control Center</h1>
        <p className="text-sm text-slate-400">
          What is the AI doing? Is it working? Where is it failing?
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
        <KpiTile label="Active Signals" value={kpis?.active_signals ?? 0} live />
        <KpiTile label="Regime" value={kpis?.current_regime ?? "—"} />
        <KpiTile label="Models" value={kpis?.models_tracked ?? 0} />
        <KpiTile label="Calibration Error" value={Number(kpis?.calibration_error ?? 0).toFixed(3)} tone="warn" />
        <KpiTile label="Drift Warnings" value={kpis?.drift_warnings ?? 0} tone={(kpis?.drift_warnings ?? 0) > 0 ? "bad" : "good"} />
        <div className="rounded-lg border border-surface-border bg-surface-raised p-4">
          <p className="text-xs uppercase text-slate-400">System</p>
          <div className="mt-3">
            <StatusBadge status={kpis?.system_status ?? "DEGRADED"} />
          </div>
        </div>
      </div>

      <Card title="Live Signals Snapshot">
        <SignalMonitoringPanel data={(data?.signals as Record<string, unknown>) ?? null} />
      </Card>

      <Card title="Drift & Trust Monitoring">
        <DriftPanel data={(data?.drift as Record<string, unknown>) ?? null} />
      </Card>
    </div>
  );
}
