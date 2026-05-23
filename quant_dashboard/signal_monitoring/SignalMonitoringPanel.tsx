"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "@/components/ui/Card";
import { ChartFrame } from "@/components/charts/ChartFrame";
import type { SignalFeedItem } from "@/lib/types";

export function SignalMonitoringPanel({ data }: { data: Record<string, unknown> | null }) {
  const feed = (data?.live_feed as SignalFeedItem[]) ?? [];
  const quality = (data?.quality as Record<string, unknown>) ?? {};

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Live Signal Feed" subtitle="Latest ensemble outputs" className="lg:col-span-2">
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {feed.map((signal) => (
            <article
              key={`${signal.ticker}-${signal.timestamp}`}
              className="rounded-lg border border-surface-border bg-surface p-3 font-mono text-sm"
            >
              <div className="flex items-center justify-between">
                <span className="text-accent-cyan">{signal.ticker}</span>
                <span className="text-accent-green">{signal.signal_type}</span>
              </div>
              <p className="mt-2 text-slate-300">
                Probability: {(signal.probability * 100).toFixed(0)}%
              </p>
              <p className="text-slate-400">
                Expected Return: {(signal.expected_return * 100).toFixed(1)}%
              </p>
              <p className="text-slate-500">Regime: {signal.regime}</p>
            </article>
          ))}
        </div>
      </Card>

      <Card title="Win Rate by Probability Bucket">
        <ChartFrame>
          <BarChart data={(quality.win_rate_by_probability_bucket as object[]) ?? []}>
            <CartesianGrid stroke="#1e2a38" strokeDasharray="3 3" />
            <XAxis dataKey="bucket" stroke="#64748b" fontSize={11} />
            <YAxis stroke="#64748b" fontSize={11} />
            <Tooltip contentStyle={{ background: "#121820", border: "1px solid #1e2a38" }} />
            <Bar dataKey="actual" fill="#22d3ee" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ChartFrame>
      </Card>

      <Card title="Signal Frequency">
        <ChartFrame>
          <LineChart data={(quality.signal_frequency as object[]) ?? []}>
            <CartesianGrid stroke="#1e2a38" strokeDasharray="3 3" />
            <XAxis dataKey="date" stroke="#64748b" fontSize={11} />
            <YAxis stroke="#64748b" fontSize={11} />
            <Tooltip contentStyle={{ background: "#121820", border: "1px solid #1e2a38" }} />
            <Line type="monotone" dataKey="count" stroke="#34d399" dot={false} />
          </LineChart>
        </ChartFrame>
      </Card>
    </div>
  );
}
