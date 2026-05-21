create table if not exists public.user_entitlements (
  user_id uuid primary key references auth.users(id) on delete cascade,
  access_level text not null default 'free' check (access_level in ('free', 'pro', 'elite')),
  active_entitlements jsonb not null default '[]'::jsonb,
  revenuecat_app_user_id text,
  product_id text,
  expires_at timestamptz,
  source text not null default 'revenuecat',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_user_entitlements_level
  on public.user_entitlements (access_level, expires_at);

create table if not exists public.watchlist_alert_preferences (
  user_id uuid not null references auth.users(id) on delete cascade,
  stock_id uuid not null references public.stocks(id) on delete cascade,
  alerts_enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, stock_id)
);

create index if not exists idx_watchlist_alert_preferences_user
  on public.watchlist_alert_preferences (user_id);

create table if not exists public.notification_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  stock_id uuid references public.stocks(id) on delete set null,
  event_type text not null check (
    event_type in ('buy', 'sell', 'portfolio_risk', 'regime_change')
  ),
  title text not null,
  body text not null,
  data jsonb not null default '{}'::jsonb,
  status text not null default 'pending' check (status in ('pending', 'sent', 'failed')),
  attempts integer not null default 0 check (attempts >= 0),
  last_error text,
  created_at timestamptz not null default now(),
  sent_at timestamptz
);

create index if not exists idx_notification_events_status_created
  on public.notification_events (status, created_at desc);

create index if not exists idx_notification_events_user_created
  on public.notification_events (user_id, created_at desc);

alter table public.user_entitlements enable row level security;
alter table public.watchlist_alert_preferences enable row level security;
alter table public.notification_events enable row level security;

create policy user_entitlements_select_own
  on public.user_entitlements for select
  to authenticated
  using ((select auth.uid()) = user_id);

create policy watchlist_alert_preferences_select_own
  on public.watchlist_alert_preferences for select
  to authenticated
  using ((select auth.uid()) = user_id);

create policy watchlist_alert_preferences_insert_own
  on public.watchlist_alert_preferences for insert
  to authenticated
  with check ((select auth.uid()) = user_id);

create policy watchlist_alert_preferences_update_own
  on public.watchlist_alert_preferences for update
  to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy notification_events_select_own
  on public.notification_events for select
  to authenticated
  using ((select auth.uid()) = user_id);

grant select on public.user_entitlements to authenticated;
grant select, insert, update on public.watchlist_alert_preferences to authenticated;
grant select on public.notification_events to authenticated;

grant select, insert, update, delete on public.user_entitlements,
  public.watchlist_alert_preferences,
  public.notification_events
to service_role;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_user_entitlements_updated_at on public.user_entitlements;
create trigger trg_user_entitlements_updated_at
  before update on public.user_entitlements
  for each row execute function public.set_updated_at();

drop trigger if exists trg_watchlist_alert_preferences_updated_at
  on public.watchlist_alert_preferences;
create trigger trg_watchlist_alert_preferences_updated_at
  before update on public.watchlist_alert_preferences
  for each row execute function public.set_updated_at();

create or replace function public.enqueue_alert_push()
returns trigger
language plpgsql
as $$
declare
  ticker text;
  probability_pct integer;
  expected_return_pct numeric;
  alert_title text;
begin
  if new.alert_type not in ('buy', 'sell', 'risk') then
    return new;
  end if;

  if exists (
    select 1
    from public.watchlist_alert_preferences pref
    where pref.user_id = new.user_id
      and pref.stock_id = new.stock_id
      and pref.alerts_enabled = false
  ) then
    return new;
  end if;

  select stocks.ticker into ticker
  from public.stocks
  where stocks.id = new.stock_id;

  probability_pct := round(new.probability * 100);
  expected_return_pct := round((new.expected_return * 100)::numeric, 1);
  alert_title := case
    when new.alert_type = 'buy' then 'BUY ' || coalesce(ticker, '')
    when new.alert_type = 'sell' then 'SELL ' || coalesce(ticker, '')
    else 'Portfolio risk alert'
  end;

  insert into public.notification_events (
    user_id,
    stock_id,
    event_type,
    title,
    body,
    data
  ) values (
    new.user_id,
    new.stock_id,
    case when new.alert_type = 'risk' then 'portfolio_risk' else new.alert_type end,
    trim(alert_title),
    'Probability: ' || probability_pct || '%, Expected return: ' || expected_return_pct || '%',
    jsonb_build_object(
      'stock_id', new.stock_id,
      'ticker', ticker,
      'signal_type', new.alert_type,
      'alert_id', new.id
    )
  );

  return new;
end;
$$;

drop trigger if exists trg_alerts_enqueue_push on public.alerts;
create trigger trg_alerts_enqueue_push
  after insert on public.alerts
  for each row execute function public.enqueue_alert_push();

create or replace function public.enqueue_regime_change_push()
returns trigger
language plpgsql
as $$
begin
  insert into public.notification_events (
    user_id,
    event_type,
    title,
    body,
    data
  )
  select distinct
    devices.user_id,
    'regime_change',
    'Regime change: ' || new.current_regime,
    'Confidence: ' || round(new.confidence * 100) || '%',
    jsonb_build_object(
      'regime', new.current_regime,
      'confidence', new.confidence,
      'timestamp', new.timestamp
    )
  from public.user_devices devices
  where devices.is_active = true;

  return new;
end;
$$;

drop trigger if exists trg_market_regimes_enqueue_push on public.market_regimes;
create trigger trg_market_regimes_enqueue_push
  after insert on public.market_regimes
  for each row execute function public.enqueue_regime_change_push();

alter table public.user_entitlements replica identity full;
alter table public.watchlist_alert_preferences replica identity full;
alter table public.notification_events replica identity full;

do $$
begin
  if exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
    alter publication supabase_realtime add table public.user_entitlements;
    alter publication supabase_realtime add table public.watchlist_alert_preferences;
    alter publication supabase_realtime add table public.notification_events;
  end if;
exception
  when duplicate_object then null;
end $$;
