"use client";

import { useCallback, useEffect, useState } from "react";
import { subscribeDashboardMetrics } from "@/lib/supabase";

export function useDashboardData<T>(
  loader: () => Promise<T>,
  refreshMs = 15000,
): { data: T | null; error: string | null; loading: boolean; refresh: () => void } {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const payload = await loader();
      setData(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  }, [loader]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, refreshMs);
    const unsubscribe = subscribeDashboardMetrics(refresh);
    return () => {
      clearInterval(interval);
      unsubscribe();
    };
  }, [refresh, refreshMs]);

  return { data, error, loading, refresh };
}
