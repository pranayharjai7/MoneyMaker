# MoneyMaker Backend

FastAPI backend for an AI trading assistant that ingests stock prices, computes technical indicators, runs model signals, combines them into an ensemble, and sends authenticated mobile-facing alerts.

## Architecture

- `api/`: FastAPI app, Supabase Auth JWT verification, mobile endpoints.
- `data_pipeline/`: Alpha Vantage, Finnhub, and Polygon adapters plus Supabase storage.
- `features/`: RSI, MACD, moving averages, Bollinger bands, ATR volatility, volume momentum.
- `models/`: modular trading models with a shared prediction contract.
- `calibration/`: isotonic/Platt probability calibration from realized prediction outcomes.
- `regime/`: SPX-referenced market regime detection.
- `meta_model/`: Sharpe-aware stacking model for final buy/sell probabilities.
- `ensemble/`: production signal generation entry point backed by the adaptive meta-model.
- `portfolio/`: fractional-Kelly, volatility-scaled allocation optimizer.
- `simulation/`: paper-trading backtest engine with slippage, costs, and partial fills.
- `alerts/`: buy/sell alert rules and alert persistence.
- `feedback/`: prediction outcome evaluation and rolling model performance metrics.
- `signal_quality/`: live signal outcome evaluation and regime-specific model ranking.
- `drift_detection/`: anti-overfitting drift scoring and model weight controls.
- `notification_control/`: adaptive throttling, cooldowns, and user trust metrics.
- `paper_analytics/`: mobile-ready paper portfolio, equity curve, and trade history views.
- `reliability/`: retry, idempotency, queue deduplication, dead letters, and circuit breakers.
- `observability/`: JSON logs, correlation IDs, metrics, and health checks.
- `analytics_api/`: production dashboard endpoints.
- `guardrails/`: safety caps, defensive mode, and signal audit tracing.
- `jobs/`: Celery worker and beat tasks.
- `db/`: Supabase client, repository, and SQL migrations.
- `tests/`: pytest coverage for ingestion, features, models, ensemble, alerts, and API routes.

## Setup

1. Copy `.env.example` to `.env` and fill in Supabase and market-data keys.
2. Apply `db/migrations/001_initial_schema.sql` in the Supabase SQL editor or via your migration workflow.
3. From the repository root, install dependencies:

```bash
pip install -r backend/requirements.txt
```

4. Run the API:

```bash
uvicorn backend.api.main:app --reload
```

5. Start Redis for local development.

If you have Docker Desktop, this starts only Redis:

```bash
docker compose -f backend/docker-compose.yml up -d redis
```

If Docker is not installed on Windows, install a local Redis-compatible server instead:

```powershell
winget install --id Redis.Redis -e
redis-server
```

6. Run Celery locally. On Windows, use the solo pool:

```bash
celery -A backend.jobs.celery_app.celery_app worker --pool=solo --loglevel=INFO
celery -A backend.jobs.celery_app.celery_app beat --loglevel=INFO
```

For quick development without Redis/Celery, run a job directly:

```bash
python -m backend.jobs.run_once full_signal_pipeline
```

Or start everything with Docker Compose:

```bash
docker compose -f backend/docker-compose.yml up --build
```

## Required Endpoints

- `GET /stocks`
- `GET /stocks/{ticker}`
- `GET /signals`
- `GET /signals/{ticker}`
- `GET /watchlist`
- `POST /watchlist/add`
- `GET /portfolio`
- `GET /alerts`
- `POST /alerts/read`
- `GET /model-performance`
- `GET /feedback-summary`
- `GET /calibration-status`
- `GET /regime`
- `GET /portfolio-weights`
- `GET /backtest-results`
- `GET /health/system`
- `GET /health/models`
- `GET /health/realtime`
- `GET /health/notifications`
- `GET /analytics/signals`
- `GET /analytics/models`
- `GET /analytics/regimes`
- `GET /analytics/notifications`
- `GET /analytics/paper-performance`
- `GET /analytics/paper-history`
- `GET /analytics/paper-equity-curve`
- `GET /analytics/paper-regime-returns`

All mobile endpoints expect `Authorization: Bearer <supabase-access-token>`.

## Notes

This service produces probabilistic research signals and alerting infrastructure. It should be reviewed, monitored, and compliance-approved before being used for real-money trading decisions.
