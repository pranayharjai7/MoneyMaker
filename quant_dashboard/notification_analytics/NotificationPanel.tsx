"use client";

import { Bar, BarChart, CartesianGrid, Tooltip, XAxis, YAxis } from "recharts";
import { Card } from "@/components/ui/Card";
import { ChartFrame } from "@/components/charts/ChartFrame";
import { KpiTile } from "@/components/ui/KpiTile";

export function NotificationPanel({ data }: { data: Record<string, unknown> | null }) {
  const funnel = (data?.funnel as { stage: string; count: number }[]) ?? [];
  const summary = (data?.summary as Record<string, number>) ?? {};

  return (
    <div className="grid gap-4">
      <div className="grid gap-4 md:grid-cols-3">
        <KpiTile label="Sent" value={summary.notifications_sent ?? 0} />
        <KpiTile label="Opened" value={summary.opened ?? 0} tone="good" />
        <KpiTile label="Fatigue Score" value={Number(data?.fatigue_score ?? 0).toFixed(2)} tone="warn" />
      </div>
      <Card title="Engagement Funnel">
        <ChartFrame>
          <BarChart data={funnel} layout="vertical">
            <CartesianGrid stroke="#1e2a38" />
            <XAxis type="number" stroke="#64748b" />
            <YAxis type="category" dataKey="stage" stroke="#64748b" width={100} />
            <Tooltip contentStyle={{ background: "#121820", border: "1px solid #1e2a38" }} />
            <Bar dataKey="count" fill="#34d399" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ChartFrame>
      </Card>
    </div>
  );
}
