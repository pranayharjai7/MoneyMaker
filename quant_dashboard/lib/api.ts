import type { OverviewPayload } from "@/lib/types";
import { buildDashboardAuthHeaders } from "@/lib/dashboard-auth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function fetchDashboard<T>(path: string, init?: RequestInit): Promise<T> {
  const authHeaders = await buildDashboardAuthHeaders();
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    if (response.status === 401) {
      throw new Error(
        `Dashboard API ${path} failed: 401 (unauthorized). ` +
          "Set NEXT_PUBLIC_DASHBOARD_API_KEY in quant_dashboard/.env.local and DASHBOARD_API_KEY in backend/.env, " +
          "or sign in at /login with Supabase.",
      );
    }
    throw new Error(`Dashboard API ${path} failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export const dashboardApi = {
  overview: () => fetchDashboard<OverviewPayload>("/dashboard/overview"),
  signals: (limit = 1000) => fetchDashboard<Record<string, unknown>>(`/dashboard/signals?limit=${limit}`),
  models: () => fetchDashboard<Record<string, unknown>>("/dashboard/models"),
  calibration: () => fetchDashboard<Record<string, unknown>>("/dashboard/calibration"),
  regimes: () => fetchDashboard<Record<string, unknown>>("/dashboard/regimes"),
  replay: (replayRunId?: string, snapshotDate?: string) => {
    const params = new URLSearchParams();
    if (replayRunId) params.set("replay_run_id", replayRunId);
    if (snapshotDate) params.set("snapshot_date", snapshotDate);
    const query = params.toString();
    return fetchDashboard<Record<string, unknown>>(`/dashboard/replay${query ? `?${query}` : ""}`);
  },
  risk: () => fetchDashboard<Record<string, unknown>>("/dashboard/risk"),
  notifications: () => fetchDashboard<Record<string, unknown>>("/dashboard/notifications"),
  drift: () => fetchDashboard<Record<string, unknown>>("/dashboard/drift"),
  infrastructure: () => fetchDashboard<Record<string, unknown>>("/dashboard/infrastructure"),
  audit: () => fetchDashboard<Record<string, unknown>>("/dashboard/audit"),
  auditDetail: (auditId: string) => fetchDashboard<Record<string, unknown>>(`/dashboard/audit/${auditId}`),
};
