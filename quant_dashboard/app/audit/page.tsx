"use client";

import { useCallback } from "react";
import { dashboardApi } from "@/lib/api";
import { useDashboardData } from "@/lib/hooks/useDashboardData";
import { AuditPanel } from "@/audit_center/AuditPanel";

export default function AuditPage() {
  const loader = useCallback(() => dashboardApi.audit(), []);
  const { data, error, loading } = useDashboardData(loader);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-white">Audit & Explainability</h1>
      {loading && <p className="text-slate-500">Loading audit traces…</p>}
      {error && <p className="text-accent-red">{error}</p>}
      <AuditPanel data={data} />
    </div>
  );
}
