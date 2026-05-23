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

Set `NEXT_PUBLIC_API_BASE_URL` to your backend and `NEXT_PUBLIC_DASHBOARD_AUTH_TOKEN` to a valid Supabase JWT for authenticated dashboard routes.

## Database

Apply `backend/db/migrations/015_phase6_quant_control_center.sql` in the Supabase SQL editor.
