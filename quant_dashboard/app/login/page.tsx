"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (!supabase) {
    return (
      <div className="mx-auto max-w-md space-y-4 p-8">
        <h1 className="text-xl font-semibold text-white">Dashboard sign-in</h1>
        <p className="text-sm text-slate-400">
          Supabase is not configured. Use{" "}
          <code className="text-accent-cyan">NEXT_PUBLIC_DASHBOARD_API_KEY</code> in{" "}
          <code className="text-accent-cyan">.env.local</code> instead (must match backend{" "}
          <code className="text-accent-cyan">DASHBOARD_API_KEY</code>).
        </p>
        <Link href="/" className="text-sm text-accent-cyan hover:underline">
          Back to dashboard
        </Link>
      </div>
    );
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });
    setLoading(false);
    if (signInError) {
      setError(signInError.message);
      return;
    }
    router.push("/");
    router.refresh();
  }

  return (
    <div className="mx-auto max-w-md space-y-6 p-8">
      <div>
        <h1 className="text-2xl font-semibold text-white">Quant Control — Sign in</h1>
        <p className="mt-1 text-sm text-slate-400">Use your Supabase operator account.</p>
      </div>
      <form onSubmit={onSubmit} className="space-y-4">
        <label className="block text-sm">
          <span className="text-slate-400">Email</span>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded border border-surface-border bg-surface px-3 py-2"
          />
        </label>
        <label className="block text-sm">
          <span className="text-slate-400">Password</span>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded border border-surface-border bg-surface px-3 py-2"
          />
        </label>
        {error && <p className="text-sm text-accent-red">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded bg-accent-cyan/20 py-2 text-accent-cyan hover:bg-accent-cyan/30 disabled:opacity-50"
        >
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <p className="text-xs text-slate-500">
        Local dev without Supabase users? Set matching{" "}
        <code>NEXT_PUBLIC_DASHBOARD_API_KEY</code> and backend <code>DASHBOARD_API_KEY</code>.
      </p>
    </div>
  );
}
