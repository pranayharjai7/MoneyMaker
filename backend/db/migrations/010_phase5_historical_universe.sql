-- Phase 5.1: Historical market universe system
-- Run in Supabase SQL editor after migrations 001-009.

create table if not exists public.stock_universes (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  description text,
  created_at timestamptz not null default now(),
  constraint stock_universes_name_slug check (name ~ '^[a-z][a-z0-9_]*$')
);

create table if not exists public.universe_memberships (
  universe_id uuid not null references public.stock_universes(id) on delete cascade,
  stock_id uuid not null references public.stocks(id) on delete cascade,
  added_at timestamptz not null default now(),
  primary key (universe_id, stock_id)
);

create index if not exists idx_universe_memberships_stock
  on public.universe_memberships (stock_id);

create index if not exists idx_universe_memberships_universe_added
  on public.universe_memberships (universe_id, added_at desc);

comment on table public.stock_universes is
  'Configurable stock universes for historical backfill and replay.';
comment on table public.universe_memberships is
  'Many-to-many membership between universes and stocks.';
