create table if not exists public.portfolio_allocations (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null,
  stock_id uuid not null references public.stocks(id) on delete cascade,
  ticker text not null,
  sector text,
  allocation double precision not null check (allocation >= 0 and allocation <= 1),
  expected_return double precision not null,
  risk_score double precision not null check (risk_score between 0 and 1),
  volatility double precision not null check (volatility >= 0),
  signal_timestamp timestamptz not null,
  optimizer_method text not null default 'fractional_kelly_vol_scaled',
  rationale jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_portfolio_allocations_run
  on public.portfolio_allocations (run_id, allocation desc);

create index if not exists idx_portfolio_allocations_created
  on public.portfolio_allocations (created_at desc);

alter table public.portfolio_allocations enable row level security;

create policy portfolio_allocations_read_authenticated
  on public.portfolio_allocations for select
  to authenticated
  using (true);

grant select on public.portfolio_allocations to authenticated;
grant select, insert on public.portfolio_allocations to service_role;
