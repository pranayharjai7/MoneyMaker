"use client";

import { Card } from "@/components/ui/Card";
import { KpiTile } from "@/components/ui/KpiTile";

export function RegimeAnalyticsPanel({ data }: { data: Record<string, unknown> | null }) {
  const current = (data?.current as Record<string, unknown>) ?? {};
  const timeline = (data?.timeline as Record<string, unknown>[]) ?? [];
  const heatmap = (data?.strategy_performance_heatmap as Record<string, unknown>[]) ?? [];

  return (
    <div className="grid gap-4">
      <div className="grid gap-4 md:grid-cols-3">
        <KpiTile label="Current Regime" value={String(current.regime ?? "—")} live />
        <KpiTile label="Confidence" value={`${((Number(current.confidence) || 0) * 100).toFixed(0)}%`} />
        <KpiTile label="Volatility Proxy" value={Number(current.volatility_proxy ?? 0).toFixed(2)} />
      </div>

      <Card title="Regime Timeline">
        <div className="flex flex-wrap gap-2">
          {timeline.map((item, index) => (
            <span
              key={`${item.regime}-${index}`}
              className="rounded-full border border-surface-border px-3 py-1 text-xs font-mono"
            >
              {String(item.regime)}
            </span>
          ))}
        </div>
      </Card>

      <Card title="Strategy Performance by Regime">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500">
                <th className="py-2">Strategy</th>
                {Object.keys(heatmap[0] ?? {})
                  .filter((key) => key !== "strategy")
                  .map((regime) => (
                    <th key={regime}>{regime}</th>
                  ))}
              </tr>
            </thead>
            <tbody>
              {heatmap.map((row) => (
                <tr key={String(row.strategy)} className="border-t border-surface-border">
                  <td className="py-2 font-mono text-accent-cyan">{String(row.strategy)}</td>
                  {Object.entries(row)
                    .filter(([key]) => key !== "strategy")
                    .map(([regime, sharpe]) => (
                      <td key={regime} className="font-mono">
                        {Number(sharpe).toFixed(2)}
                      </td>
                    ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
