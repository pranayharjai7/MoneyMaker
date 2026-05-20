create table if not exists public.calibrated_predictions (
  id uuid primary key default gen_random_uuid(),
  prediction_id uuid not null references public.model_predictions(id) on delete cascade,
  model_name text not null,
  stock_id uuid not null references public.stocks(id) on delete cascade,
  raw_probability double precision not null check (raw_probability between 0 and 1),
  calibrated_probability double precision not null check (calibrated_probability between 0 and 1),
  confidence_interval_low double precision not null check (confidence_interval_low between 0 and 1),
  confidence_interval_high double precision not null check (confidence_interval_high between 0 and 1),
  calibration_method text not null check (
    calibration_method in ('isotonic_regression', 'platt_scaling', 'empirical_fallback')
  ),
  sample_size integer not null default 0 check (sample_size >= 0),
  calibration_error double precision not null default 0 check (calibration_error >= 0),
  timestamp timestamptz not null,
  created_at timestamptz not null default now(),
  unique (prediction_id)
);

create index if not exists idx_calibrated_predictions_stock_timestamp
  on public.calibrated_predictions (stock_id, timestamp desc);

create index if not exists idx_calibrated_predictions_model_timestamp
  on public.calibrated_predictions (model_name, timestamp desc);

alter table public.calibrated_predictions enable row level security;

create policy calibrated_predictions_read_authenticated
  on public.calibrated_predictions for select
  to authenticated
  using (true);

grant select on public.calibrated_predictions to authenticated;
grant select, insert, update, delete on public.calibrated_predictions to service_role;
