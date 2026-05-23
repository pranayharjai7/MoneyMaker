"use client";

import { Treemap, ResponsiveContainer, Tooltip } from "recharts";
import { Card } from "@/components/ui/Card";
import { ChartFrame } from "@/components/charts/ChartFrame";
import { KpiTile } from "@/components/ui/KpiTile";

export function RiskPanel({ data }: { data: Record<string, unknown> | null }) {
  const treemap = (data?.allocation_treemap as { name: string; value: number }[]) ?? [];
  const sectors = (data?.sector_exposure as { sector: string; exposure: number }[]) ?? [];
  const summary = (data?.summary as Record<string, number>) ?? {};

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <KpiTile label="Concentration Risk" value={Number(summary.concentration_risk ?? 0).toFixed(2)} tone="warn" />
      <KpiTile label="Volatility Exposure" value={Number(summary.volatility_exposure ?? 0).toFixed(3)} />
      <KpiTile label="Positions" value={summary.position_count ?? 0} />

      <Card title="Portfolio Allocation" className="lg:col-span-2">
        <ChartFrame height={300}>
          <ResponsiveContainer>
            <Treemap data={treemap} dataKey="value" nameKey="name" stroke="#0b0f14" fill="#22d3ee" />
          </ResponsiveContainer>
        </ChartFrame>
      </Card>

      <Card title="Sector Exposure">
        <ul className="space-y-2 text-sm">
          {sectors.map((row) => (
            <li key={row.sector} className="flex justify-between border-b border-surface-border py-2">
              <span>{row.sector}</span>
              <span className="font-mono">{(row.exposure * 100).toFixed(1)}%</span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
