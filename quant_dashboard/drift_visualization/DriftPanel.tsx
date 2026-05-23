"use client";

import { Line, LineChart, CartesianGrid, Tooltip, XAxis, YAxis } from "recharts";
import { Card } from "@/components/ui/Card";
import { ChartFrame } from "@/components/charts/ChartFrame";

export function DriftPanel({ data }: { data: Record<string, unknown> | null }) {
  const timeline = (data?.timeline as { model_name: string; drift_score: number; created_at: string }[]) ?? [];
  const warnings = (data?.warnings as { level: string; message: string }[]) ?? [];

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Drift Score Timeline" className="lg:col-span-2">
        <ChartFrame>
          <LineChart data={timeline}>
            <CartesianGrid stroke="#1e2a38" />
            <XAxis dataKey="created_at" stroke="#64748b" fontSize={10} />
            <YAxis stroke="#64748b" />
            <Tooltip contentStyle={{ background: "#121820", border: "1px solid #1e2a38" }} />
            <Line type="monotone" dataKey="drift_score" stroke="#f87171" dot />
          </LineChart>
        </ChartFrame>
      </Card>

      <Card title="Automatic Warnings" className="lg:col-span-2">
        <ul className="space-y-2 text-sm">
          {warnings.length === 0 && <li className="text-slate-500">No active drift warnings.</li>}
          {warnings.map((warning) => (
            <li
              key={warning.message}
              className="rounded border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-amber-200"
            >
              {warning.message}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
