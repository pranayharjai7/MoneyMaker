# MoneyMaker Mobile

Flutter mobile product layer for the MoneyMaker AI trading backend.

## What is included

- Supabase Auth, Postgres reads, RLS-safe user tables, and Realtime streams.
- Dark fintech UI with dashboard, signals, explainability, watchlist, alerts, portfolio, insights, and subscription screens.
- FCM token registration and foreground/background notification handlers.
- RevenueCat-style entitlement architecture with local SDK support and backend-backed access control.
- Hive cache for last-known signals, alerts, regime, portfolio, watchlist, and insights.
- Supabase SQL and Edge Functions for notification outbox and RevenueCat webhook validation.

## Run

Install Flutter, then from `mobile/`:

```bash
flutter pub get
flutter run \
  --dart-define=SUPABASE_URL=https://your-project-ref.supabase.co \
  --dart-define=SUPABASE_ANON_KEY=your-publishable-or-anon-key \
  --dart-define=MONEYMAKER_API_BASE_URL=http://10.0.2.2:8000 \
  --dart-define=REVENUECAT_ANDROID_API_KEY=goog_xxx \
  --dart-define=REVENUECAT_IOS_API_KEY=appl_xxx
```

Run `flutterfire configure` before production builds, or provide the Firebase dart-defines shown in `.env.example`.

## Supabase setup

Apply `../backend/db/migrations/008_mobile_product_layer.sql`, deploy the Edge Functions under `../supabase/functions`, and create a Database Webhook:

- Table: `notification_events`
- Event: `INSERT`
- Type: Supabase Edge Function
- Function: `push-signal`
- Headers: include the service key auth header

RevenueCat webhooks should point to `revenuecat-webhook` and include a shared secret in `REVENUECAT_WEBHOOK_SECRET`.

## OAuth Redirect URLs

Add these URLs in Supabase Dashboard → Authentication → URL Configuration → Redirect URLs:

```text
com.moneymaker.mobile://login-callback/
http://127.0.0.1:54321/login-callback
```

The custom scheme is used by Android/iOS. The localhost callback is used only for Windows/macOS/Linux desktop debugging so the browser can hand the OAuth code back to the running desktop app.
