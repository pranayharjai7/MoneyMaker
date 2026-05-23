"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { dashboardApi } from "@/lib/api";

export function AuditPanel({ data }: { data: Record<string, unknown> | null }) {
  const audits = (data?.recent_audits as { id: string; ticker?: string; timestamp?: string; blocked?: boolean }[]) ?? [];
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);

  async function loadDetail(auditId: string) {
    const detail = await dashboardApi.auditDetail(auditId);
    setSelected(detail);
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Recent Signal Audits">
        <ul className="divide-y divide-surface-border text-sm">
          {audits.map((audit) => (
            <li key={audit.id}>
              <button
                type="button"
                className="flex w-full items-center justify-between py-3 text-left hover:text-accent-cyan"
                onClick={() => loadDetail(audit.id)}
              >
                <span className="font-mono">{audit.ticker ?? audit.id}</span>
                <span className="text-xs text-slate-500">{audit.timestamp}</span>
              </button>
            </li>
          ))}
        </ul>
      </Card>

      <Card title="Why was this signal generated?">
        {selected ? (
          <ol className="space-y-3 text-sm">
            {((selected.reasoning_chain as { step: string; detail: unknown }[]) ?? []).map((step) => (
              <li key={step.step} className="rounded border border-surface-border p-3">
                <p className="mb-1 text-xs uppercase text-accent-cyan">{step.step}</p>
                <pre className="overflow-auto text-xs text-slate-400">
                  {JSON.stringify(step.detail, null, 2)}
                </pre>
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-slate-500">Select an audit entry to view the reasoning chain.</p>
        )}
      </Card>
    </div>
  );
}
