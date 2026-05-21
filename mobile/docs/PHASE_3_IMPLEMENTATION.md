# Phase 3 Mobile Product Layer

## Completed Phases

1. Project setup + architecture
   - Generated Android and iOS Flutter project shells.
   - Added clean architecture folders under `lib/core`, `lib/data`, `lib/domain`, `lib/presentation`, and `lib/features`.
   - Standardized Riverpod, GoRouter, dark fintech theme, and shared UI primitives.

2. Supabase integration
   - Supabase Auth email/password login.
   - JWT-backed FastAPI calls through `ApiClient`.
   - Supabase Realtime streams for `ensemble_signals`, `alerts`, `user_watchlists`, and `user_entitlements`.
   - Hive cache for last-known signals, alerts, portfolio, watchlist, regime, model performance, calibration, and entitlements.

3. Dashboard UI + realtime signals
   - Dashboard metrics for top buy signals, market regime, portfolio risk, and active alerts.
   - Signal stream with realtime/delayed badge based on entitlement.
   - Signal cards match the product contract: ticker, signal type, probability, expected return, risk, and hold window.

4. Watchlist + portfolio
   - Watchlist ticker add flow, live probability merge from latest signals, and per-stock alert toggles.
   - Portfolio holdings, AI recommended allocation, risk exposure, and sector breakdown.

5. Alerts system
   - Realtime alert list.
   - Mark-read support through `/alerts/read`.
   - Pro entitlement gate for alert access.

6. Push notifications
   - FCM token registration in `user_devices`.
   - Foreground/local notification display.
   - Supabase migration for `notification_events`.
   - Alert/regime triggers that enqueue DB-driven push events.
   - `push-signal` Edge Function sends FCM HTTP v1 notifications.

7. Subscription system
   - RevenueCat SDK configuration.
   - Plan screen for Free, Pro, and Elite.
   - Restore purchases support.
   - Supabase `user_entitlements` mirror table.
   - `revenuecat-webhook` Edge Function for server-side entitlement validation.

8. Insights + explainability
   - Insights screen for market regime explanation, model performance, and calibration confidence.
   - Elite-gated signal explainability screen showing model agreement, regime context, and risk reasoning.

## Supabase Assets

Apply this migration:

```text
backend/db/migrations/008_mobile_product_layer.sql
```

Deploy these Edge Functions:

```text
supabase/functions/push-signal
supabase/functions/revenuecat-webhook
```

Create a Database Webhook:

- Table: `notification_events`
- Event: `INSERT`
- Target: Edge Function `push-signal`

Set these Supabase secrets:

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
FIREBASE_PROJECT_ID
FIREBASE_SERVICE_ACCOUNT_JSON
REVENUECAT_WEBHOOK_SECRET
```

`FIREBASE_SERVICE_ACCOUNT_JSON` may be replaced with:

```text
FIREBASE_CLIENT_EMAIL
FIREBASE_PRIVATE_KEY
```

## Verification

Completed locally:

```bash
flutter pub get
flutter analyze
flutter test
flutter build apk --debug
```

Not run locally:

```bash
flutter test integration_test
```

The integration test requires a connected Android/iOS device or emulator. No supported mobile device was connected on this Windows host.
