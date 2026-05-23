-- Phase 5.2: Multi-year historical OHLCV backfill support
-- Run after 010_phase5_historical_universe.sql

create table if not exists public.price_backfill_state (
  stock_id uuid not null references public.stocks(id) on delete cascade,
  resolution text not null default 'daily' check (resolution in ('daily', 'hourly')),
  target_start_date date not null,
  target_end_date date not null,
  earliest_stored_date date,
  latest_stored_date date,
  last_backfilled_through date,
  last_provider text,
  status text not null default 'pending'
    check (status in ('pending', 'in_progress', 'completed', 'failed')),
  bars_stored integer not null default 0 check (bars_stored >= 0),
  chunks_completed integer not null default 0 check (chunks_completed >= 0),
  chunks_total integer not null default 0 check (chunks_total >= 0),
  last_error text,
  updated_at timestamptz not null default now(),
  primary key (stock_id, resolution)
);

create index if not exists idx_price_backfill_state_status
  on public.price_backfill_state (status, updated_at desc);

-- Ascending time order speeds replay scans and range backfills.
create index if not exists idx_stock_prices_stock_timestamp_asc
  on public.stock_prices (stock_id, timestamp asc);

-- Range queries for feature generation and replay windows.
create index if not exists idx_stock_prices_timestamp
  on public.stock_prices (timestamp desc);

comment on table public.price_backfill_state is
  'Per-stock backfill progress for real OHLCV ingestion (no synthetic data).';
