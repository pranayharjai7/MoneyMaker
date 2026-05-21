from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from backend.api.auth import AuthUser, get_current_user
from backend.api.deps import get_repository
from backend.api.main import create_app


class FakeRepository:
    def list_stocks(self):
        return [
            {
                "id": "stock-1",
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "sector": "Technology",
                "exchange": "NASDAQ",
                "created_at": "2026-05-20T00:00:00+00:00",
            }
        ]

    def get_stock_by_ticker(self, ticker: str):
        return self.list_stocks()[0] if ticker.upper() == "AAPL" else None

    def list_signals(self):
        return []

    def list_signals_for_quality(self, cutoff_timestamp: str, limit: int = 1000):
        return []

    def get_signals_for_ticker(self, ticker: str):
        return []

    def list_watchlist(self, user_id: str):
        return []

    def add_watchlist_stock(self, user_id: str, stock_id: str):
        return {
            "id": "watch-1",
            "user_id": user_id,
            "stock_id": stock_id,
            "created_at": "2026-05-20T00:00:00+00:00",
        }

    def list_portfolio(self, user_id: str):
        return []

    def list_latest_portfolio_allocations(self):
        return [
            {
                "id": "allocation-1",
                "run_id": "run-1",
                "stock_id": "stock-1",
                "ticker": "AAPL",
                "sector": "Technology",
                "allocation": 0.07,
                "expected_return": 0.04,
                "risk_score": 0.3,
                "volatility": 0.02,
                "signal_timestamp": "2026-05-20T00:00:00+00:00",
                "optimizer_method": "fractional_kelly_vol_scaled",
                "rationale": {},
                "created_at": "2026-05-20T00:00:00+00:00",
            }
        ]

    def list_alerts(self, user_id: str, unread_only: bool = False):
        return []

    def mark_alerts_read(self, user_id: str, alert_ids: list[str]):
        return []

    def list_model_performance(self):
        return [
            {
                "model_name": "momentum",
                "accuracy": 0.75,
                "brier_score": 0.18,
                "calibration_error": 0.08,
                "sharpe_contribution": 1.2,
                "sample_size": 16,
                "window_days": 90,
                "updated_at": "2026-05-20T00:00:00+00:00",
            }
        ]

    def list_model_regime_performance(self):
        return [
            {
                "model_name": "momentum",
                "regime": "BULL TREND",
                "win_rate": 0.7,
                "sharpe_ratio": 1.4,
                "average_return": 0.02,
                "sample_size": 12,
                "profit_factor": 1.8,
                "max_drawdown": -0.03,
                "updated_at": "2026-05-20T00:00:00+00:00",
            }
        ]

    def list_live_signal_performance(self, limit: int = 1000):
        return [
            {
                "signal_id": "signal-1",
                "stock_id": "stock-1",
                "model_used": "momentum",
                "regime": "BULL TREND",
                "predicted_return": 0.03,
                "actual_return": 0.04,
                "horizon_days": 5,
                "outcome": "win",
                "pnl": 0.04,
                "created_at": "2026-05-20T00:00:00+00:00",
            }
        ][:limit]

    def list_recent_model_drift_events(
        self,
        since_timestamp: str | None = None,
        limit: int = 100,
    ):
        return [
            {
                "model_name": "mean_reversion",
                "drift_score": 0.55,
                "drift_type": "calibration_decay",
                "severity": "medium",
                "created_at": "2026-05-20T00:00:00+00:00",
            }
        ][:limit]

    def list_prediction_outcomes(self, since_timestamp: str | None = None, limit: int = 10000):
        return [
            {
                "model_name": "momentum",
                "horizon_days": 1,
                "error": 0.01,
                "success": True,
                "timestamp": "2026-05-19T21:00:00+00:00",
            }
        ]

    def latest_calibrated_prediction_timestamp(self):
        return "2026-05-20T00:00:00+00:00"

    def list_calibrated_predictions(
        self,
        stock_id: str | None = None,
        timestamp: str | None = None,
        limit: int = 1000,
    ):
        return [
            {
                "model_name": "momentum",
                "calibration_method": "empirical_fallback",
                "sample_size": 1,
                "calibration_error": 0.1,
                "timestamp": "2026-05-20T00:00:00+00:00",
            }
        ]

    def latest_market_regime(self):
        return {
            "timestamp": "2026-05-20T00:00:00+00:00",
            "current_regime": "BULL TREND",
            "confidence": 0.81,
            "spx_trend": 0.05,
            "volatility_proxy": 0.16,
            "moving_average_spread": 0.03,
            "sector_correlation_shift": 0.04,
            "liquidity_score": 0.92,
            "feature_payload": {"reference_ticker": "SPX"},
        }

    def get_market_regime_at_or_before(self, timestamp: str):
        return self.latest_market_regime()

    def latest_backtest_result(self):
        return {
            "id": "backtest-1",
            "strategy_return": 0.124,
            "max_drawdown": -0.051,
            "sharpe_ratio": 1.8,
            "trade_count": 25,
            "win_rate": 0.6,
            "max_win_streak": 4,
            "max_loss_streak": 2,
            "total_transaction_costs": 0.002,
            "average_slippage_bps": 5.0,
            "parameters": {},
            "result_payload": {},
            "created_at": "2026-05-20T00:00:00+00:00",
        }

    def list_notification_metrics(self, limit: int = 1000):
        return [
            {
                "user_id": "user-1",
                "notifications_sent": 10,
                "opened": 6,
                "ignored": 2,
                "engagement_score": 0.6,
            }
        ][:limit]

    def list_recent_notification_events(
        self,
        status: str | None = None,
        limit: int = 100,
    ):
        rows = [
            {
                "status": "sent",
                "created_at": "2026-05-20T00:00:00+00:00",
            }
        ]
        if status:
            rows = [row for row in rows if row["status"] == status]
        return rows[:limit]

    def list_signal_audit_logs(self, limit: int = 100):
        return [
            {
                "stock_id": "stock-1",
                "timestamp": "2026-05-20T00:00:00+00:00",
                "guardrail_decision": {"allowed": True, "violations": []},
            }
        ][:limit]


def test_stocks_endpoint_uses_repository_override() -> None:
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: FakeRepository()
    app.dependency_overrides[get_current_user] = lambda: AuthUser(
        id="user-1", email="test@example.com", role="authenticated", claims={}
    )
    client = TestClient(app)

    response = client.get("/stocks")

    assert response.status_code == 200
    assert response.json()[0]["ticker"] == "AAPL"


def test_feedback_endpoints_use_repository_override() -> None:
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: FakeRepository()
    app.dependency_overrides[get_current_user] = lambda: AuthUser(
        id="user-1", email="test@example.com", role="authenticated", claims={}
    )
    client = TestClient(app)

    performance_response = client.get("/model-performance")
    summary_response = client.get("/feedback-summary")

    assert performance_response.status_code == 200
    assert performance_response.json()[0]["model_name"] == "momentum"
    assert summary_response.status_code == 200
    assert summary_response.json()["total_outcomes"] == 1


def test_calibration_status_endpoint_uses_repository_override() -> None:
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: FakeRepository()
    app.dependency_overrides[get_current_user] = lambda: AuthUser(
        id="user-1", email="test@example.com", role="authenticated", claims={}
    )
    client = TestClient(app)

    response = client.get("/calibration-status")

    assert response.status_code == 200
    assert response.json()["models"][0]["model_name"] == "momentum"


def test_regime_endpoint_uses_repository_override() -> None:
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: FakeRepository()
    app.dependency_overrides[get_current_user] = lambda: AuthUser(
        id="user-1", email="test@example.com", role="authenticated", claims={}
    )
    client = TestClient(app)

    response = client.get("/regime")

    assert response.status_code == 200
    assert response.json()["current_regime"] == "BULL TREND"


def test_portfolio_weights_endpoint_uses_repository_override() -> None:
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: FakeRepository()
    app.dependency_overrides[get_current_user] = lambda: AuthUser(
        id="user-1", email="test@example.com", role="authenticated", claims={}
    )
    client = TestClient(app)

    response = client.get("/portfolio-weights")

    assert response.status_code == 200
    assert response.json()[0]["ticker"] == "AAPL"


def test_backtest_results_endpoint_uses_repository_override() -> None:
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: FakeRepository()
    app.dependency_overrides[get_current_user] = lambda: AuthUser(
        id="user-1", email="test@example.com", role="authenticated", claims={}
    )
    client = TestClient(app)

    response = client.get("/backtest-results")

    assert response.status_code == 200
    assert response.json()["sharpe_ratio"] == 1.8


def test_phase4_analytics_endpoints_use_repository_override() -> None:
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: FakeRepository()
    app.dependency_overrides[get_current_user] = lambda: AuthUser(
        id="user-1", email="test@example.com", role="authenticated", claims={}
    )
    client = TestClient(app)

    signals_response = client.get("/analytics/signals")
    models_response = client.get("/analytics/models")
    notifications_response = client.get("/analytics/notifications")
    paper_response = client.get("/analytics/paper-performance")
    health_response = client.get("/health/notifications")

    assert signals_response.status_code == 200
    assert signals_response.json()["summary"]["sample_size"] == 1
    assert models_response.status_code == 200
    assert models_response.json()["drift"]["active_model_weight_multipliers"]["mean_reversion"] == 0.6
    assert notifications_response.status_code == 200
    assert notifications_response.json()["summary"]["notifications_sent"] == 10
    assert paper_response.status_code == 200
    assert paper_response.json()["portfolio_return"] == 0.124
    assert health_response.status_code == 200
