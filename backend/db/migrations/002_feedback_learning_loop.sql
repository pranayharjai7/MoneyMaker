create table if not exists public.prediction_outcomes (
  id uuid primary key default gen_random_uuid(),
  stock_id uuid not null references public.stocks(id) on delete cascade,
  prediction_id uuid not null references public.model_predictions(id) on delete cascade,
  timestamp timestamptz not null,
  horizon_days integer not null check (horizon_days in (1, 3, 5, 10)),
  model_name text not null,
  predicted_probability double precision not null check (predicted_probability between 0 and 1),
  predicted_return double precision not null,
  predicted_direction text not null check (predicted_direction in ('up', 'down', 'neutral')),
  actual_return double precision not null,
  error double precision not null,
  success boolean not null,
  created_at timestamptz not null default now(),
  unique (prediction_id, horizon_days)
);

create index if not exists idx_prediction_outcomes_stock_timestamp
  on public.prediction_outcomes (stock_id, timestamp desc);

create index if not exists idx_prediction_outcomes_model_timestamp
  on public.prediction_outcomes (model_name, timestamp desc);

create table if not exists public.model_performance (
  model_name text primary key,
  accuracy double precision not null check (accuracy between 0 and 1),
  brier_score double precision not null check (brier_score >= 0),
  calibration_error double precision not null check (calibration_error >= 0),
  sharpe_contribution double precision not null,
  sample_size integer not null default 0 check (sample_size >= 0),
  window_days integer not null default 90 check (window_days > 0),
  updated_at timestamptz not null default now()
);

alter table public.prediction_outcomes enable row level security;
alter table public.model_performance enable row level security;

create policy prediction_outcomes_read_authenticated
  on public.prediction_outcomes for select
  to authenticated
  using (true);

create policy model_performance_read_authenticated
  on public.model_performance for select
  to authenticated
  using (true);

grant select on public.prediction_outcomes,
  public.model_performance
to authenticated;

grant select, insert, update, delete on public.prediction_outcomes,
  public.model_performance
to service_role;
