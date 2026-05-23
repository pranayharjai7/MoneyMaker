"use client";

import { useCallback } from "react";
import { dashboardApi } from "@/lib/api";
import { useDashboardData } from "@/lib/hooks/useDashboardData";
import { NotificationPanel } from "@/notification_analytics/NotificationPanel";

export default function NotificationsPage() {
  const loader = useCallback(() => dashboardApi.notifications(), []);
  const { data, error, loading } = useDashboardData(loader);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-white">Notification Effectiveness</h1>
      {loading && <p className="text-slate-500">Loading engagement analytics…</p>}
      {error && <p className="text-accent-red">{error}</p>}
      <NotificationPanel data={data} />
    </div>
  );
}
