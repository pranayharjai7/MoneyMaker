"use client";

import { Line, LineChart, CartesianGrid, Tooltip, XAxis, YAxis, Bar, BarChart } from "recharts";
import { Card } from "@/components/ui/Card";
import { ChartFrame } from "@/components/charts/ChartFrame";
import { KpiTile } from "@/components/ui/KpiTile";

export function CalibrationPanel({ data }: { data: Record<string, unknown> | null }) {
  const curve = (data?.calibration_curve as { predicted: number; actual: number }[]) ?? [];
  const brier = (data?.brier_scores as Record<string, number>) ?? {};
  const brierSeries = Object.entries(brier).map(([period, score]) => ({ period, score }));

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <KpiTile label="Aggregate Calibration Error" value={Number(data?.aggregate_calibration_error ?? 0).toFixed(3)} />
      <KpiTile label="Daily Brier" value={brier.daily?.toFixed(3) ?? "—"} tone="warn" />
      <KpiTile label="Monthly Brier" value={brier.monthly?.toFixed(3) ?? "—"} />

      <Card title="Reliability Diagram" className="lg:col-span-2">
        <ChartFrame>
          <BarChart data={curve}>
            <CartesianGrid stroke="#1e2a38" />
            <XAxis dataKey="predicted" stroke="#64748b" />
            <YAxis stroke="#64748b" />
            <Tooltip contentStyle={{ background: "#121820", border: "1px solid #1e2a38" }} />
            <Bar dataKey="predicted" fill="#64748b" name="Predicted" />
            <Bar dataKey="actual" fill="#22d3ee" name="Actual" />
          </BarChart>
        </ChartFrame>
      </Card>

      <Card title="Brier Score Tracking">
        <ChartFrame height={220}>
          <LineChart data={brierSeries}>
            <CartesianGrid stroke="#1e2a38" />
            <XAxis dataKey="period" stroke="#64748b" />
            <YAxis stroke="#64748b" />
            <Line type="monotone" dataKey="score" stroke="#34d399" />
          </LineChart>
        </ChartFrame>
      </Card>
    </div>
  );
}
