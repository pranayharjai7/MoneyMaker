create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  created_at timestamptz not null default now()
);

create table if not exists public.stocks (
  id uuid primary key default gen_random_uuid(),
  ticker text not null unique,
  company_name text not null,
  sector text,
  exchange text,
  created_at timestamptz not null default now(),
  constraint stocks_ticker_uppercase check (ticker = upper(ticker))
);

create table if not exists public.stock_prices (
  id uuid primary key default gen_random_uuid(),
  stock_id uuid not null references public.stocks(id) on delete cascade,
  timestamp timestamptz not null,
  open double precision not null,
  high double precision not null,
  low double precision not null,
  close double precision not null,
  volume double precision not null default 0,
  created_at timestamptz not null default now(),
  unique (stock_id, timestamp)
);

create index if not exists idx_stock_prices_stock_timestamp
  on public.stock_prices (stock_id, timestamp desc);

create table if not exists public.technical_indicators (
  id uuid primary key default gen_random_uuid(),
  stock_id uuid not null references public.stocks(id) on delete cascade,
  timestamp timestamptz not null,
  rsi double precision,
  macd double precision,
  macd_signal double precision,
  sma_20 double precision,
  sma_50 double precision,
  bollinger_upper double precision,
  bollinger_lower double precision,
  volatility double precision,
  volume_momentum double precision,
  created_at timestamptz not null default now(),
  unique (stock_id, timestamp)
);

create index if not exists idx_technical_indicators_stock_timestamp
  on public.technical_indicators (stock_id, timestamp desc);

create table if not exists public.model_predictions (
  id uuid primary key default gen_random_uuid(),
  stock_id uuid not null references public.stocks(id) on delete cascade,
  timestamp timestamptz not null,
  model_name text not null,
  probability_up double precision not null check (probability_up between 0 and 1),
  expected_return double precision not null,
  confidence double precision not null check (confidence between 0 and 1),
  created_at timestamptz not null default now(),
  unique (stock_id, timestamp, model_name)
);

create index if not exists idx_model_predictions_stock_timestamp
  on public.model_predictions (stock_id, timestamp desc);

create table if not exists public.ensemble_signals (
  id uuid primary key default gen_random_uuid(),
  stock_id uuid not null references public.stocks(id) on delete cascade,
  timestamp timestamptz not null,
  buy_probability double precision not null check (buy_probability between 0 and 1),
  sell_probability double precision not null check (sell_probability between 0 and 1),
  expected_return double precision not null,
  risk_score double precision not null check (risk_score between 0 and 1),
  suggested_hold_days integer not null default 1 check (suggested_hold_days > 0),
  signal_type text not null check (signal_type in ('buy', 'sell', 'neutral')),
  created_at timestamptz not null default now(),
  unique (stock_id, timestamp)
);

create index if not exists idx_ensemble_signals_stock_timestamp
  on public.ensemble_signals (stock_id, timestamp desc);

create table if not exists public.user_watchlists (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  stock_id uuid not null references public.stocks(id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (user_id, stock_id)
);

create index if not exists idx_user_watchlists_user
  on public.user_watchlists (user_id, created_at desc);

create table if not exists public.user_portfolio (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  stock_id uuid not null references public.stocks(id) on delete cascade,
  shares double precision not null check (shares >= 0),
  average_price double precision not null check (average_price >= 0),
  created_at timestamptz not null default now(),
  unique (user_id, stock_id)
);

create index if not exists idx_user_portfolio_user
  on public.user_portfolio (user_id, created_at desc);

create table if not exists public.alerts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  stock_id uuid not null references public.stocks(id) on delete cascade,
  alert_type text not null check (alert_type in ('buy', 'sell', 'risk', 'neutral')),
  probability double precision not null check (probability between 0 and 1),
  expected_return double precision not null,
  risk_score double precision not null check (risk_score between 0 and 1),
  source_signal_timestamp timestamptz,
  created_at timestamptz not null default now(),
  is_read boolean not null default false,
  unique (user_id, stock_id, alert_type, source_signal_timestamp)
);

create index if not exists idx_alerts_user_created
  on public.alerts (user_id, created_at desc);

create table if not exists public.user_devices (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  platform text not null check (platform in ('ios', 'android')),
  push_token text not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  unique (platform, push_token)
);

create index if not exists idx_user_devices_user
  on public.user_devices (user_id, is_active);

alter table public.profiles enable row level security;
alter table public.stocks enable row level security;
alter table public.stock_prices enable row level security;
alter table public.technical_indicators enable row level security;
alter table public.model_predictions enable row level security;
alter table public.ensemble_signals enable row level security;
alter table public.user_watchlists enable row level security;
alter table public.user_portfolio enable row level security;
alter table public.alerts enable row level security;
alter table public.user_devices enable row level security;

create policy profiles_select_own
  on public.profiles for select
  to authenticated
  using ((select auth.uid()) = id);

create policy profiles_update_own
  on public.profiles for update
  to authenticated
  using ((select auth.uid()) = id)
  with check ((select auth.uid()) = id);

create policy stocks_read_authenticated
  on public.stocks for select
  to authenticated
  using (true);

create policy stock_prices_read_authenticated
  on public.stock_prices for select
  to authenticated
  using (true);

create policy technical_indicators_read_authenticated
  on public.technical_indicators for select
  to authenticated
  using (true);

create policy model_predictions_read_authenticated
  on public.model_predictions for select
  to authenticated
  using (true);

create policy ensemble_signals_read_authenticated
  on public.ensemble_signals for select
  to authenticated
  using (true);

create policy user_watchlists_select_own
  on public.user_watchlists for select
  to authenticated
  using ((select auth.uid()) = user_id);

create policy user_watchlists_insert_own
  on public.user_watchlists for insert
  to authenticated
  with check ((select auth.uid()) = user_id);

create policy user_watchlists_delete_own
  on public.user_watchlists for delete
  to authenticated
  using ((select auth.uid()) = user_id);

create policy user_portfolio_select_own
  on public.user_portfolio for select
  to authenticated
  using ((select auth.uid()) = user_id);

create policy user_portfolio_insert_own
  on public.user_portfolio for insert
  to authenticated
  with check ((select auth.uid()) = user_id);

create policy user_portfolio_update_own
  on public.user_portfolio for update
  to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy user_portfolio_delete_own
  on public.user_portfolio for delete
  to authenticated
  using ((select auth.uid()) = user_id);

create policy alerts_select_own
  on public.alerts for select
  to authenticated
  using ((select auth.uid()) = user_id);

create policy alerts_update_own
  on public.alerts for update
  to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy user_devices_select_own
  on public.user_devices for select
  to authenticated
  using ((select auth.uid()) = user_id);

create policy user_devices_insert_own
  on public.user_devices for insert
  to authenticated
  with check ((select auth.uid()) = user_id);

create policy user_devices_update_own
  on public.user_devices for update
  to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy user_devices_delete_own
  on public.user_devices for delete
  to authenticated
  using ((select auth.uid()) = user_id);

grant usage on schema public to authenticated;

grant select on public.stocks,
  public.stock_prices,
  public.technical_indicators,
  public.model_predictions,
  public.ensemble_signals
to authenticated;

grant select, update on public.profiles to authenticated;
grant select, insert, delete on public.user_watchlists to authenticated;
grant select, insert, update, delete on public.user_portfolio to authenticated;
grant select, update on public.alerts to authenticated;
grant select, insert, update, delete on public.user_devices to authenticated;

alter table public.alerts replica identity full;
alter table public.ensemble_signals replica identity full;

do $$
begin
  if exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
    alter publication supabase_realtime add table public.alerts;
    alter publication supabase_realtime add table public.ensemble_signals;
  end if;
exception
  when duplicate_object then null;
end $$;
