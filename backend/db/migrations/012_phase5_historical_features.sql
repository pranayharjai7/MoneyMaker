-- Phase 5.3: Historical feature store (time-correct, no leakage)
-- Run after 011_phase5_historical_backfill.sql

create table if not exists public.historical_features (
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
  atr double precision,
  rolling_beta_spy double precision,
  sector_relative_strength double precision,
  volatility_percentile double precision,
  trend_persistence double precision,
  created_at timestamptz not null default now(),
  primary key (stock_id, timestamp)
);

create index if not exists idx_historical_features_stock_timestamp
  on public.historical_features (stock_id, timestamp asc);

create index if not exists idx_historical_features_timestamp
  on public.historical_features (timestamp desc);

comment on table public.historical_features is
  'Point-in-time features computed from real OHLCV only (past data at each timestamp).';
