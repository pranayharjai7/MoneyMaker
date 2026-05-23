import { supabase } from "@/lib/supabase";

/** Headers for backend /dashboard/* (Supabase JWT, static token, or shared API key). */
export async function buildDashboardAuthHeaders(): Promise<HeadersInit> {
  const headers: Record<string, string> = {};

  const apiKey = process.env.NEXT_PUBLIC_DASHBOARD_API_KEY?.trim();
  if (apiKey) {
    headers["X-Dashboard-Key"] = apiKey;
  }

  const staticToken = process.env.NEXT_PUBLIC_DASHBOARD_AUTH_TOKEN?.trim();
  if (staticToken) {
    headers.Authorization = `Bearer ${staticToken}`;
    return headers;
  }

  if (supabase) {
    const { data } = await supabase.auth.getSession();
    const accessToken = data.session?.access_token;
    if (accessToken) {
      headers.Authorization = `Bearer ${accessToken}`;
    }
  }

  return headers;
}

export function hasDashboardAuthConfig(): boolean {
  return Boolean(
    process.env.NEXT_PUBLIC_DASHBOARD_API_KEY?.trim() ||
      process.env.NEXT_PUBLIC_DASHBOARD_AUTH_TOKEN?.trim() ||
      (process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY),
  );
}
