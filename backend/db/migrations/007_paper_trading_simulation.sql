create table if not exists public.backtest_results (
  id uuid primary key default gen_random_uuid(),
  strategy_return double precision not null,
  max_drawdown double precision not null,
  sharpe_ratio double precision not null,
  trade_count integer not null default 0 check (trade_count >= 0),
  win_rate double precision not null default 0 check (win_rate between 0 and 1),
  max_win_streak integer not null default 0 check (max_win_streak >= 0),
  max_loss_streak integer not null default 0 check (max_loss_streak >= 0),
  total_transaction_costs double precision not null default 0 check (total_transaction_costs >= 0),
  average_slippage_bps double precision not null default 0 check (average_slippage_bps >= 0),
  parameters jsonb not null default '{}'::jsonb,
  result_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_backtest_results_created
  on public.backtest_results (created_at desc);

alter table public.backtest_results enable row level security;

create policy backtest_results_read_authenticated
  on public.backtest_results for select
  to authenticated
  using (true);

grant select on public.backtest_results to authenticated;
grant select, insert on public.backtest_results to service_role;
