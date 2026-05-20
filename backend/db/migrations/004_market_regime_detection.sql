create table if not exists public.market_regimes (
  id uuid primary key default gen_random_uuid(),
  timestamp timestamptz not null,
  current_regime text not null check (
    current_regime in (
      'BULL TREND',
      'BEAR TREND',
      'SIDEWAYS',
      'HIGH VOLATILITY',
      'LOW LIQUIDITY'
    )
  ),
  confidence double precision not null check (confidence between 0 and 1),
  spx_trend double precision not null default 0,
  volatility_proxy double precision not null default 0,
  moving_average_spread double precision not null default 0,
  sector_correlation_shift double precision not null default 0,
  liquidity_score double precision not null default 1 check (liquidity_score between 0 and 1),
  feature_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (timestamp)
);

create index if not exists idx_market_regimes_timestamp
  on public.market_regimes (timestamp desc);

alter table public.market_regimes enable row level security;

create policy market_regimes_read_authenticated
  on public.market_regimes for select
  to authenticated
  using (true);

grant select on public.market_regimes to authenticated;
grant select, insert, update, delete on public.market_regimes to service_role;
