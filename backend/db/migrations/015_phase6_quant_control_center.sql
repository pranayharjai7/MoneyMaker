-- Phase 6: Quant Control Center operational intelligence tables

create table if not exists public.dashboard_metrics (
  id uuid primary key default gen_random_uuid(),
  metric_key text not null,
  metric_group text not null,
  value double precision not null,
  dimensions jsonb not null default '{}'::jsonb,
  recorded_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create index if not exists idx_dashboard_metrics_key_recorded
  on public.dashboard_metrics (metric_key, recorded_at desc);

create index if not exists idx_dashboard_metrics_group_recorded
  on public.dashboard_metrics (metric_group, recorded_at desc);

create table if not exists public.drift_visualizations (
  id uuid primary key default gen_random_uuid(),
  model_name text not null,
  drift_score double precision not null check (drift_score >= 0),
  feature_drift jsonb not null default '{}'::jsonb,
  severity text not null check (severity in ('low', 'medium', 'high', 'critical')),
  alert_message text,
  snapshot_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create index if not exists idx_drift_visualizations_model_snapshot
  on public.drift_visualizations (model_name, snapshot_at desc);

create table if not exists public.replay_snapshots (
  id uuid primary key default gen_random_uuid(),
  replay_run_id uuid references public.replay_runs(id) on delete cascade,
  snapshot_date date not null,
  ai_state jsonb not null default '{}'::jsonb,
  equity double precision not null default 0,
  drawdown double precision not null default 0,
  sharpe double precision not null default 0,
  regime text,
  created_at timestamptz not null default now(),
  unique (replay_run_id, snapshot_date)
);

create index if not exists idx_replay_snapshots_run_date
  on public.replay_snapshots (replay_run_id, snapshot_date desc);

create table if not exists public.notification_engagement (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  period_start date not null,
  period_end date not null,
  sent integer not null default 0 check (sent >= 0),
  opened integer not null default 0 check (opened >= 0),
  dismissed integer not null default 0 check (dismissed >= 0),
  viewed integer not null default 0 check (viewed >= 0),
  acted_upon integer not null default 0 check (acted_upon >= 0),
  fatigue_score double precision not null default 0 check (fatigue_score between 0 and 1),
  created_at timestamptz not null default now(),
  unique (user_id, period_start, period_end)
);

create index if not exists idx_notification_engagement_period
  on public.notification_engagement (period_end desc);

create table if not exists public.infra_metrics (
  id uuid primary key default gen_random_uuid(),
  component text not null,
  metric_name text not null,
  value double precision not null,
  status text not null check (status in ('ok', 'degraded', 'critical')),
  metadata jsonb not null default '{}'::jsonb,
  recorded_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create index if not exists idx_infra_metrics_component_recorded
  on public.infra_metrics (component, recorded_at desc);

alter table public.dashboard_metrics enable row level security;
alter table public.drift_visualizations enable row level security;
alter table public.replay_snapshots enable row level security;
alter table public.notification_engagement enable row level security;
alter table public.infra_metrics enable row level security;

create policy dashboard_metrics_read_authenticated
  on public.dashboard_metrics for select
  to authenticated
  using (true);

create policy drift_visualizations_read_authenticated
  on public.drift_visualizations for select
  to authenticated
  using (true);

create policy replay_snapshots_read_authenticated
  on public.replay_snapshots for select
  to authenticated
  using (true);

create policy notification_engagement_read_authenticated
  on public.notification_engagement for select
  to authenticated
  using (true);

create policy infra_metrics_read_authenticated
  on public.infra_metrics for select
  to authenticated
  using (true);

create policy dashboard_metrics_service_role_all
  on public.dashboard_metrics for all
  to service_role
  using (true)
  with check (true);

create policy drift_visualizations_service_role_all
  on public.drift_visualizations for all
  to service_role
  using (true)
  with check (true);

create policy replay_snapshots_service_role_all
  on public.replay_snapshots for all
  to service_role
  using (true)
  with check (true);

create policy notification_engagement_service_role_all
  on public.notification_engagement for all
  to service_role
  using (true)
  with check (true);

create policy infra_metrics_service_role_all
  on public.infra_metrics for all
  to service_role
  using (true)
  with check (true);

alter table public.dashboard_metrics replica identity full;
alter table public.drift_visualizations replica identity full;
alter table public.replay_snapshots replica identity full;
alter table public.notification_engagement replica identity full;
alter table public.infra_metrics replica identity full;

do $$
begin
  if exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
    alter publication supabase_realtime add table public.dashboard_metrics;
    alter publication supabase_realtime add table public.drift_visualizations;
    alter publication supabase_realtime add table public.signal_audit_log;
  end if;
exception
  when duplicate_object then null;
end $$;
