-- Phase 7: Trade Planning and Execution Intelligence tables

create table if not exists public.trade_plans (
  id uuid primary key default gen_random_uuid(),
  stock_id uuid not null references public.stocks(id) on delete cascade,
  current_price double precision not null,
  forecast_window_min_days integer not null default 5,
  forecast_window_max_days integer not null default 7,
  bullish_probability double precision not null check (bullish_probability between 0 and 1),
  bearish_probability double precision not null check (bearish_probability between 0 and 1),
  neutral_probability double precision not null check (neutral_probability between 0 and 1),
  confidence text not null check (confidence in ('LOW', 'MEDIUM', 'HIGH')),
  regime_context text not null,
  weekly_bias text not null,
  daily_bias text not null,
  intraday_bias text not null,
  suggested_entry_low double precision not null,
  suggested_entry_high double precision not null,
  suggested_entry_price double precision not null,
  entry_type text not null,
  entry_timing text not null,
  entry_score double precision not null check (entry_score between 0 and 100),
  stop_loss double precision not null,
  max_suggested_risk_pct double precision not null,
  risk_reward_ratio double precision not null,
  expected_hold_min_days integer not null,
  expected_hold_max_days integer not null,
  suggested_execution text not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_trade_plans_stock_created
  on public.trade_plans (stock_id, created_at desc);

create table if not exists public.trade_targets (
  id uuid primary key default gen_random_uuid(),
  trade_plan_id uuid not null references public.trade_plans(id) on delete cascade,
  target_label text not null check (target_label in ('TP1', 'TP2', 'TP3')),
  target_price double precision not null,
  probability double precision not null check (probability between 0 and 1),
  created_at timestamptz not null default now(),
  unique (trade_plan_id, target_label)
);

create table if not exists public.trade_stop_updates (
  id uuid primary key default gen_random_uuid(),
  trade_plan_id uuid not null references public.trade_plans(id) on delete cascade,
  old_stop_price double precision not null,
  new_stop_price double precision not null,
  reason text not null,
  updated_at timestamptz not null default now()
);

create index if not exists idx_trade_stop_updates_plan_updated
  on public.trade_stop_updates (trade_plan_id, updated_at desc);

create table if not exists public.trade_alerts (
  id uuid primary key default gen_random_uuid(),
  trade_plan_id uuid not null references public.trade_plans(id) on delete cascade,
  alert_type text not null check (alert_type in ('entry', 'risk', 'exit', 'regime')),
  message text not null,
  triggered_at timestamptz not null default now(),
  is_read boolean not null default false
);

create index if not exists idx_trade_alerts_plan_triggered
  on public.trade_alerts (trade_plan_id, triggered_at desc);

create table if not exists public.trade_reasoning (
  id uuid primary key default gen_random_uuid(),
  trade_plan_id uuid not null references public.trade_plans(id) on delete cascade,
  factor_type text not null,
  factor_text text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.execution_recommendations (
  id uuid primary key default gen_random_uuid(),
  trade_plan_id uuid not null references public.trade_plans(id) on delete cascade,
  situation text not null,
  suggested_order_type text not null check (suggested_order_type in ('limit', 'market', 'stop')),
  order_price double precision not null,
  reason text not null,
  created_at timestamptz not null default now()
);

-- Enable RLS
alter table public.trade_plans enable row level security;
alter table public.trade_targets enable row level security;
alter table public.trade_stop_updates enable row level security;
alter table public.trade_alerts enable row level security;
alter table public.trade_reasoning enable row level security;
alter table public.execution_recommendations enable row level security;

-- Read policies for authenticated users
create policy trade_plans_read_authenticated
  on public.trade_plans for select to authenticated using (true);

create policy trade_targets_read_authenticated
  on public.trade_targets for select to authenticated using (true);

create policy trade_stop_updates_read_authenticated
  on public.trade_stop_updates for select to authenticated using (true);

create policy trade_alerts_read_authenticated
  on public.trade_alerts for select to authenticated using (true);

create policy trade_reasoning_read_authenticated
  on public.trade_reasoning for select to authenticated using (true);

create policy execution_recommendations_read_authenticated
  on public.execution_recommendations for select to authenticated using (true);

-- Full policies for service_role
create policy trade_plans_service_role_all
  on public.trade_plans for all to service_role using (true) with check (true);

create policy trade_targets_service_role_all
  on public.trade_targets for all to service_role using (true) with check (true);

create policy trade_stop_updates_service_role_all
  on public.trade_stop_updates for all to service_role using (true) with check (true);

create policy trade_alerts_service_role_all
  on public.trade_alerts for all to service_role using (true) with check (true);

create policy trade_reasoning_service_role_all
  on public.trade_reasoning for all to service_role using (true) with check (true);

create policy execution_recommendations_service_role_all
  on public.execution_recommendations for all to service_role using (true) with check (true);

-- Grants
grant select on public.trade_plans,
  public.trade_targets,
  public.trade_stop_updates,
  public.trade_alerts,
  public.trade_reasoning,
  public.execution_recommendations
to authenticated;

-- Replica identities
alter table public.trade_plans replica identity full;
alter table public.trade_targets replica identity full;
alter table public.trade_stop_updates replica identity full;
alter table public.trade_alerts replica identity full;
alter table public.trade_reasoning replica identity full;
alter table public.execution_recommendations replica identity full;

-- Add tables to realtime publication if it exists
do $$
begin
  if exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
    alter publication supabase_realtime add table public.trade_plans;
    alter publication supabase_realtime add table public.trade_targets;
    alter publication supabase_realtime add table public.trade_stop_updates;
    alter publication supabase_realtime add table public.trade_alerts;
    alter publication supabase_realtime add table public.trade_reasoning;
    alter publication supabase_realtime add table public.execution_recommendations;
  end if;
exception
  when duplicate_object then null;
end $$;
