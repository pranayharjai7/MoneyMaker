-- Phase 5.5-5.8: Signals calibration, bootstrap training, regime learning, analytics
-- Run after 013_phase5_historical_replay.sql

alter table public.historical_signals
  add column if not exists calibrated_probability double precision
    check (calibrated_probability is null or calibrated_probability between 0 and 1);

create table if not exists public.historical_calibration_snapshots (
  id uuid primary key default gen_random_uuid(),
  replay_run_id uuid not null references public.replay_runs(id) on delete cascade,
  model_name text not null,
  as_of_date date not null,
  calibration_method text not null,
  sample_size integer not null default 0 check (sample_size >= 0),
  calibration_error double precision not null default 0 check (calibration_error >= 0),
  empirical_rate double precision,
  created_at timestamptz not null default now(),
  unique (replay_run_id, model_name, as_of_date)
);

create index if not exists idx_historical_calibration_snapshots_run_date
  on public.historical_calibration_snapshots (replay_run_id, as_of_date asc);

create table if not exists public.historical_regime_periods (
  id uuid primary key default gen_random_uuid(),
  replay_run_id uuid references public.replay_runs(id) on delete set null,
  regime text not null,
  start_date date not null,
  end_date date not null,
  confidence double precision not null check (confidence between 0 and 1),
  benchmark_return double precision not null default 0,
  volatility_proxy double precision not null default 0,
  created_at timestamptz not null default now(),
  unique (replay_run_id, start_date, regime)
);

create index if not exists idx_historical_regime_periods_dates
  on public.historical_regime_periods (start_date asc, end_date asc);

create table if not exists public.bootstrap_training_runs (
  id uuid primary key default gen_random_uuid(),
  replay_run_id uuid not null references public.replay_runs(id) on delete cascade,
  training_type text not null check (training_type in ('calibration', 'regime', 'meta_model', 'full')),
  status text not null default 'completed'
    check (status in ('pending', 'running', 'completed', 'failed')),
  metrics jsonb not null default '{}'::jsonb,
  meta_model_version text,
  created_at timestamptz not null default now()
);

create index if not exists idx_bootstrap_training_runs_replay
  on public.bootstrap_training_runs (replay_run_id, created_at desc);
