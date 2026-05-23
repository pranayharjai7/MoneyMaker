"use client";

import { Line, LineChart, CartesianGrid, Tooltip, XAxis, YAxis } from "recharts";
import { Card } from "@/components/ui/Card";
import { ChartFrame } from "@/components/charts/ChartFrame";

export function ModelIntelligencePanel({ data }: { data: Record<string, unknown> | null }) {
  const leaderboard = (data?.leaderboard as Record<string, unknown>[]) ?? [];
  const rolling = (data?.rolling_performance as Record<string, { index: number; value: number }[]>) ?? {};
  const firstModel = Object.keys(rolling)[0];
  const rollingData = firstModel ? rolling[firstModel] : [];

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Model Leaderboard" className="lg:col-span-2">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase text-slate-500">
              <tr>
                <th className="py-2">Model</th>
                <th>Sharpe</th>
                <th>Win Rate</th>
                <th>Drift</th>
              </tr>
            </thead>
            <tbody>
              {leaderboard.map((row) => (
                <tr key={String(row.model)} className="border-t border-surface-border">
                  <td className="py-2 font-mono text-accent-cyan">{String(row.model)}</td>
                  <td>{Number(row.sharpe).toFixed(2)}</td>
                  <td>{(Number(row.win_rate) * 100).toFixed(1)}%</td>
                  <td>{Number(row.drift).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title="Rolling Performance" subtitle={firstModel ?? "No model data"}>
        <ChartFrame>
          <LineChart data={rollingData}>
            <CartesianGrid stroke="#1e2a38" strokeDasharray="3 3" />
            <XAxis dataKey="index" stroke="#64748b" fontSize={11} />
            <YAxis stroke="#64748b" fontSize={11} />
            <Tooltip contentStyle={{ background: "#121820", border: "1px solid #1e2a38" }} />
            <Line type="monotone" dataKey="value" stroke="#fbbf24" dot={false} />
          </LineChart>
        </ChartFrame>
      </Card>
    </div>
  );
}
