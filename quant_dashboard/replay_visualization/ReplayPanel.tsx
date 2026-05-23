"use client";

import { useState } from "react";
import { Area, AreaChart, CartesianGrid, Line, LineChart, Tooltip, XAxis, YAxis } from "recharts";
import { Card } from "@/components/ui/Card";
import { ChartFrame } from "@/components/charts/ChartFrame";
import { dashboardApi } from "@/lib/api";

export function ReplayPanel({ initialData }: { initialData: Record<string, unknown> | null }) {
  const [data, setData] = useState(initialData);
  const report = (data?.report as Record<string, unknown>) ?? {};
  const equity = (report.equity_curve as { date?: string; equity: number }[]) ?? [];
  const drawdown = (data?.drawdown_curve as { date?: string; drawdown: number }[]) ?? [];
  const dates = (data?.available_snapshot_dates as string[]) ?? [];

  async function scrub(date: string) {
    const payload = await dashboardApi.replay(String(data?.selected_run_id), date);
    setData(payload);
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Historical Equity Curve" action={
        <select
          className="rounded border border-surface-border bg-surface px-2 py-1 text-xs"
          onChange={(event) => scrub(event.target.value)}
          defaultValue=""
        >
          <option value="" disabled>
            Scrub date
          </option>
          {dates.map((date) => (
            <option key={date} value={date}>
              {date}
            </option>
          ))}
        </select>
      }>
        <ChartFrame>
          <AreaChart data={equity}>
            <CartesianGrid stroke="#1e2a38" />
            <XAxis dataKey="date" stroke="#64748b" fontSize={10} />
            <YAxis stroke="#64748b" fontSize={10} />
            <Tooltip contentStyle={{ background: "#121820", border: "1px solid #1e2a38" }} />
            <Area type="monotone" dataKey="equity" stroke="#22d3ee" fill="#22d3ee33" />
          </AreaChart>
        </ChartFrame>
      </Card>

      <Card title="Drawdown">
        <ChartFrame>
          <LineChart data={drawdown}>
            <CartesianGrid stroke="#1e2a38" />
            <XAxis dataKey="date" stroke="#64748b" fontSize={10} />
            <YAxis stroke="#64748b" fontSize={10} />
            <Line type="monotone" dataKey="drawdown" stroke="#f87171" dot={false} />
          </LineChart>
        </ChartFrame>
      </Card>

      {data?.scrub_state && (
        <Card title="AI State at Selected Date" className="lg:col-span-2">
          <pre className="overflow-auto rounded bg-surface p-3 text-xs text-slate-300">
            {JSON.stringify(data.scrub_state, null, 2)}
          </pre>
        </Card>
      )}
    </div>
  );
}
