create table if not exists public.live_signal_performance (
  id uuid primary key default gen_random_uuid(),
  signal_id uuid not null references public.ensemble_signals(id) on delete cascade,
  stock_id uuid not null references public.stocks(id) on delete cascade,
  model_used text not null,
  regime text not null,
  predicted_return double precision not null,
  actual_return double precision not null,
  horizon_days integer not null check (horizon_days > 0),
  outcome text not null check (outcome in ('win', 'loss', 'flat')),
  pnl double precision not null,
  created_at timestamptz not null default now(),
  unique (signal_id, horizon_days)
);

create index if not exists idx_live_signal_performance_stock_created
  on public.live_signal_performance (stock_id, created_at desc);

create index if not exists idx_live_signal_performance_model_regime
  on public.live_signal_performance (model_used, regime, created_at desc);

create table if not exists public.model_regime_performance (
  model_name text not null,
  regime text not null,
  win_rate double precision not null check (win_rate between 0 and 1),
  sharpe_ratio double precision not null,
  average_return double precision not null,
  sample_size integer not null default 0 check (sample_size >= 0),
  profit_factor double precision not null default 0 check (profit_factor >= 0),
  max_drawdown double precision not null default 0 check (max_drawdown <= 0),
  updated_at timestamptz not null default now(),
  primary key (model_name, regime)
);

create index if not exists idx_model_regime_performance_regime
  on public.model_regime_performance (regime, sharpe_ratio desc, win_rate desc);

create table if not exists public.model_drift_events (
  id uuid primary key default gen_random_uuid(),
  model_name text not null,
  drift_score double precision not null check (drift_score >= 0),
  drift_type text not null,
  severity text not null check (severity in ('low', 'medium', 'high', 'critical')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_model_drift_events_model_created
  on public.model_drift_events (model_name, created_at desc);

create table if not exists public.notification_metrics (
  user_id uuid primary key references auth.users(id) on delete cascade,
  notifications_sent integer not null default 0 check (notifications_sent >= 0),
  opened integer not null default 0 check (opened >= 0),
  ignored integer not null default 0 check (ignored >= 0),
  engagement_score double precision not null default 0 check (engagement_score between 0 and 1),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.notification_dead_letters (
  id uuid primary key default gen_random_uuid(),
  queue_key text not null,
  payload jsonb not null default '{}'::jsonb,
  failure_reason text,
  attempts integer not null default 0 check (attempts >= 0),
  created_at timestamptz not null default now()
);

create index if not exists idx_notification_dead_letters_created
  on public.notification_dead_letters (created_at desc);

create table if not exists public.signal_audit_log (
  id uuid primary key default gen_random_uuid(),
  signal_id uuid references public.ensemble_signals(id) on delete set null,
  stock_id uuid not null references public.stocks(id) on delete cascade,
  timestamp timestamptz not null,
  models_involved jsonb not null default '[]'::jsonb,
  regime text,
  calibration_values jsonb not null default '{}'::jsonb,
  final_meta_model_output jsonb not null default '{}'::jsonb,
  guardrail_decision jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_signal_audit_log_stock_timestamp
  on public.signal_audit_log (stock_id, timestamp desc);

alter table public.live_signal_performance enable row level security;
alter table public.model_regime_performance enable row level security;
alter table public.model_drift_events enable row level security;
alter table public.notification_metrics enable row level security;
alter table public.notification_dead_letters enable row level security;
alter table public.signal_audit_log enable row level security;

create policy live_signal_performance_read_authenticated
  on public.live_signal_performance for select
  to authenticated
  using (true);

create policy model_regime_performance_read_authenticated
  on public.model_regime_performance for select
  to authenticated
  using (true);

create policy model_drift_events_read_authenticated
  on public.model_drift_events for select
  to authenticated
  using (true);

create policy notification_metrics_select_own
  on public.notification_metrics for select
  to authenticated
  using ((select auth.uid()) = user_id);

create policy signal_audit_log_read_authenticated
  on public.signal_audit_log for select
  to authenticated
  using (true);

grant select on public.live_signal_performance,
  public.model_regime_performance,
  public.model_drift_events,
  public.signal_audit_log
to authenticated;

grant select on public.notification_metrics to authenticated;

grant select, insert, update, delete on public.live_signal_performance,
  public.model_regime_performance,
  public.model_drift_events,
  public.notification_metrics,
  public.notification_dead_letters,
  public.signal_audit_log
to service_role;

drop trigger if exists trg_notification_metrics_updated_at
  on public.notification_metrics;
create trigger trg_notification_metrics_updated_at
  before update on public.notification_metrics
  for each row execute function public.set_updated_at();

alter table public.live_signal_performance replica identity full;
alter table public.model_regime_performance replica identity full;
alter table public.model_drift_events replica identity full;
alter table public.notification_metrics replica identity full;
alter table public.signal_audit_log replica identity full;

do $$
begin
  if exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
    alter publication supabase_realtime add table public.live_signal_performance;
    alter publication supabase_realtime add table public.model_regime_performance;
    alter publication supabase_realtime add table public.model_drift_events;
    alter publication supabase_realtime add table public.notification_metrics;
    alter publication supabase_realtime add table public.signal_audit_log;
  end if;
exception
  when duplicate_object then null;
end $$;
