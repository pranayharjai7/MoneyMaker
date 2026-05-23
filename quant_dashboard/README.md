# MoneyMaker Quant Control Center

Internal operational intelligence dashboard (not user-facing mobile UI).

## Stack

- Next.js 15 + TypeScript + Tailwind
- Recharts
- Supabase Realtime (dashboard_metrics, signal_audit_log)
- FastAPI `/dashboard/*` endpoints

## Run

```bash
cd quant_dashboard
cp .env.example .env.local
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_BASE_URL` to your backend.

**Auth (pick one):**

1. **Local dev (recommended):** set the same secret in both env files:
   - `backend/.env` → `DASHBOARD_API_KEY=...`
   - `quant_dashboard/.env.local` → `NEXT_PUBLIC_DASHBOARD_API_KEY=...`
2. **Supabase login:** configure `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY`, then open http://localhost:3100/login
3. **Static JWT:** `NEXT_PUBLIC_DASHBOARD_AUTH_TOKEN` = Supabase user `access_token` (expires quickly)

## Database

Apply `backend/db/migrations/015_phase6_quant_control_center.sql` in the Supabase SQL editor.
