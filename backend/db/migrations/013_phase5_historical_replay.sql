-- Phase 5.4: Historical replay engine storage
-- Run after 012_phase5_historical_features.sql

create table if not exists public.replay_runs (
  id uuid primary key default gen_random_uuid(),
  universe_name text not null,
  mode text not null check (mode in ('signal_only', 'paper_portfolio', 'adaptive')),
  start_date date not null,
  end_date date not null,
  status text not null default 'pending'
    check (status in ('pending', 'running', 'completed', 'failed', 'paused')),
  last_replay_date date,
  signals_generated integer not null default 0 check (signals_generated >= 0),
  outcomes_evaluated integer not null default 0 check (outcomes_evaluated >= 0),
  meta_model_version text not null default 'replay_v1',
  config jsonb not null default '{}'::jsonb,
  last_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_replay_runs_status_updated
  on public.replay_runs (status, updated_at desc);

create table if not exists public.historical_signals (
  id uuid primary key default gen_random_uuid(),
  replay_run_id uuid not null references public.replay_runs(id) on delete cascade,
  stock_id uuid not null references public.stocks(id) on delete cascade,
  timestamp timestamptz not null,
  signal_type text not null check (signal_type in ('buy', 'sell', 'neutral')),
  probability double precision not null check (probability between 0 and 1),
  expected_return double precision not null,
  risk_score double precision not null check (risk_score between 0 and 1),
  hold_days integer not null default 5 check (hold_days > 0),
  regime text not null,
  meta_model_version text not null,
  model_predictions jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  unique (replay_run_id, stock_id, timestamp)
);

create index if not exists idx_historical_signals_run_timestamp
  on public.historical_signals (replay_run_id, timestamp asc);

create index if not exists idx_historical_signals_stock_timestamp
  on public.historical_signals (stock_id, timestamp desc);

create table if not exists public.replay_outcomes (
  id uuid primary key default gen_random_uuid(),
  replay_run_id uuid not null references public.replay_runs(id) on delete cascade,
  historical_signal_id uuid not null references public.historical_signals(id) on delete cascade,
  stock_id uuid not null references public.stocks(id) on delete cascade,
  entry_timestamp timestamptz not null,
  exit_timestamp timestamptz not null,
  entry_price double precision not null check (entry_price > 0),
  exit_price double precision not null check (exit_price > 0),
  actual_return double precision not null,
  horizon_days integer not null check (horizon_days > 0),
  outcome text not null check (outcome in ('win', 'loss', 'flat')),
  pnl double precision not null,
  created_at timestamptz not null default now(),
  unique (historical_signal_id)
);

create index if not exists idx_replay_outcomes_run_created
  on public.replay_outcomes (replay_run_id, created_at desc);

create table if not exists public.replay_portfolio_snapshots (
  id uuid primary key default gen_random_uuid(),
  replay_run_id uuid not null references public.replay_runs(id) on delete cascade,
  snapshot_date date not null,
  cash double precision not null,
  equity double precision not null,
  positions jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  unique (replay_run_id, snapshot_date)
);

create index if not exists idx_replay_portfolio_snapshots_run_date
  on public.replay_portfolio_snapshots (replay_run_id, snapshot_date asc);
