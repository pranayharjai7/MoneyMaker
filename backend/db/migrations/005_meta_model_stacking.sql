create table if not exists public.meta_model_training_runs (
  id uuid primary key default gen_random_uuid(),
  model_type text not null check (
    model_type in ('gradient_boosting', 'logistic_regression', 'performance_weighted_fallback')
  ),
  sample_size integer not null check (sample_size >= 0),
  feature_names jsonb not null default '[]'::jsonb,
  sharpe_objective_score double precision not null default 0,
  training_window_days integer not null default 365 check (training_window_days > 0),
  updated_at timestamptz not null default now()
);

create index if not exists idx_meta_model_training_runs_updated
  on public.meta_model_training_runs (updated_at desc);

alter table public.meta_model_training_runs enable row level security;

create policy meta_model_training_runs_read_authenticated
  on public.meta_model_training_runs for select
  to authenticated
  using (true);

grant select on public.meta_model_training_runs to authenticated;
grant select, insert on public.meta_model_training_runs to service_role;
