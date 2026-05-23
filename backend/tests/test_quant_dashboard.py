from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from backend.api.auth import AuthUser, get_current_user
from backend.api.deps import get_repository
from backend.api.main import create_app
from backend.audit_center.service import explain_signal
from backend.quant_dashboard.overview import build_overview_payload
from backend.quant_dashboard.shared import brier_score, probability_buckets
from backend.replay_visualization.service import build_replay_visualization_payload
from backend.signal_monitoring.service import build_signal_monitoring_payload


class FakeQuantRepository:
    def list_signals(self, limit: int = 100):
        return [
            {
                "id": "sig-1",
                "stock_id": "stock-1",
                "timestamp": "2026-05-20T15:00:00+00:00",
                "buy_probability": 0.71,
                "sell_probability": 0.22,
                "expected_return": 0.041,
                "risk_score": 0.31,
                "signal_type": "buy",
                "stocks": {"ticker": "NVDA", "sector": "Technology"},
            }
        ][:limit]

    def latest_market_regime(self):
        return {"current_regime": "BULL TREND", "confidence": 0.82, "volatility_proxy": 0.18}

    def list_live_signal_performance(self, limit: int = 1000):
        return [
            {
                "signal_id": "sig-1",
                "predicted_return": 0.71,
                "pnl": 0.04,
                "outcome": "win",
                "model_used": "momentum",
            }
        ][:limit]

    def list_model_performance(self):
        return [
            {
                "model_name": "momentum",
                "accuracy": 0.68,
                "brier_score": 0.17,
                "calibration_error": 0.09,
                "sharpe_contribution": 1.3,
                "sample_size": 40,
            }
        ]

    def list_recent_model_drift_events(self, since_timestamp: str | None = None, limit: int = 100):
        return [
            {
                "model_name": "momentum",
                "drift_score": 0.72,
                "severity": "high",
                "created_at": "2026-05-21T12:00:00+00:00",
                "metadata": {"components": {"rsi": 0.4, "macd": 0.3}},
            }
        ][:limit]

    def list_prediction_outcomes(self, since_timestamp: str | None = None):
        return [
            {
                "model_name": "momentum",
                "predicted_probability": 0.7,
                "actual_return": 0.03,
                "created_at": "2026-05-20T12:00:00+00:00",
            },
            {
                "model_name": "momentum",
                "predicted_probability": 0.8,
                "actual_return": -0.01,
                "created_at": "2026-05-19T12:00:00+00:00",
            },
        ]

    def list_prediction_outcomes_between(self, start: str, end: str):
        return self.list_prediction_outcomes()

    def list_recent_model_predictions(self, limit: int = 1000):
        return []

    def list_recent_indicators(self, limit: int = 1000):
        return []

    def list_calibrated_predictions(self, limit: int = 500):
        return []

    def latest_calibrated_prediction_timestamp(self):
        return "2026-05-20T12:00:00+00:00"

    def list_model_regime_performance(self):
        return [
            {
                "model_name": "momentum",
                "regime": "BULL TREND",
                "win_rate": 0.7,
                "sharpe_ratio": 1.4,
            }
        ]

    def list_historical_regime_periods(self, *, replay_run_id: str | None = None, limit: int = 500):
        return [
            {
                "regime": "BULL TREND",
                "start_date": "2026-01-01",
                "end_date": "2026-03-01",
                "confidence": 0.8,
            },
            {
                "regime": "SIDEWAYS",
                "start_date": "2026-03-02",
                "end_date": "2026-05-01",
                "confidence": 0.6,
            },
        ]

    def list_replay_runs(self, *, limit: int = 20):
        return [{"id": "run-1", "universe_name": "sp500", "status": "completed"}][:limit]

    def get_replay_run(self, replay_run_id: str):
        if replay_run_id == "run-1":
            return {
                "id": "run-1",
                "universe_name": "sp500",
                "mode": "walk_forward",
                "status": "completed",
                "signals_generated": 10,
                "outcomes_evaluated": 8,
            }
        return None

    def list_historical_signals(self, *, replay_run_id: str, limit: int = 50000):
        return [{"id": "hs-1", "regime": "BULL TREND", "model_predictions": []}]

    def list_replay_outcomes(self, *, replay_run_id: str, limit: int = 50000):
        return [
            {
                "historical_signal_id": "hs-1",
                "exit_timestamp": "2026-02-01",
                "actual_return": 0.02,
                "outcome": "win",
            }
        ]

    def list_replay_portfolio_snapshots(self, *, replay_run_id: str):
        return [
            {"snapshot_date": "2026-01-01", "equity": 100000},
            {"snapshot_date": "2026-02-01", "equity": 102000},
        ]

    def list_historical_calibration_snapshots(self, *, replay_run_id: str):
        return []

    def list_replay_snapshots(self, *, replay_run_id: str | None = None, snapshot_date: str | None = None, limit: int = 500):
        return [
            {
                "replay_run_id": "run-1",
                "snapshot_date": "2026-02-01",
                "sharpe": 1.1,
                "regime": "BULL TREND",
                "ai_state": {"models": ["momentum"]},
            }
        ]

    def get_replay_snapshot_at_date(self, replay_run_id: str, snapshot_date: str):
        snapshots = self.list_replay_snapshots(replay_run_id=replay_run_id, snapshot_date=snapshot_date)
        return snapshots[0] if snapshots else None

    def list_latest_portfolio_allocations(self):
        return [
            {
                "ticker": "NVDA",
                "stock_id": "stock-1",
                "sector": "Technology",
                "allocation": 0.07,
                "expected_return": 0.04,
                "risk_score": 0.3,
                "volatility": 0.02,
                "rationale": {"kelly_fraction": 0.05},
            }
        ]

    def list_dashboard_metrics(self, *, metric_group: str | None = None, metric_key: str | None = None, limit: int = 1000):
        return []

    def list_notification_metrics(self, limit: int = 1000):
        return [{"notifications_sent": 10, "opened": 6, "ignored": 2, "engagement_score": 0.6}]

    def list_notification_engagement(self, *, limit: int = 500):
        return []

    def list_recent_notification_events(self, status: str | None = None, limit: int = 100):
        return [{"status": "sent", "created_at": "2026-05-21T12:00:00+00:00"}]

    def list_drift_visualizations(self, *, model_name: str | None = None, limit: int = 500):
        return []

    def list_signal_audit_logs(self, limit: int = 100):
        return [
            {
                "id": "audit-1",
                "timestamp": "2026-05-20T15:00:00+00:00",
                "regime": "BULL TREND",
                "models_involved": [{"model_name": "momentum", "probability_up": 0.71}],
                "calibration_values": {},
                "final_meta_model_output": {"signal_type": "buy"},
                "guardrail_decision": {"allowed": True},
            }
        ][:limit]

    def get_signal_audit_log(self, audit_id: str):
        if audit_id != "audit-1":
            return None
        row = self.list_signal_audit_logs(1)[0]
        row["stocks"] = {"ticker": "NVDA"}
        return row

    def list_infra_metrics(self, *, component: str | None = None, limit: int = 500):
        return []

    def list_stocks(self):
        return [{"id": "stock-1"}]


def test_probability_buckets_and_brier_score_accuracy() -> None:
    rows = [
        {"buy_probability": 0.7, "outcome": "win"},
        {"buy_probability": 0.7, "outcome": "loss"},
        {"buy_probability": 0.8, "outcome": "win"},
    ]
    buckets = probability_buckets(rows)
    populated = [bucket for bucket in buckets if bucket["count"] > 0]
    assert populated
    assert 0.0 <= brier_score(rows) <= 1.0


def test_signal_monitoring_payload_structure() -> None:
    payload = build_signal_monitoring_payload(FakeQuantRepository())
    assert payload["live_feed"][0]["ticker"] == "NVDA"
    assert payload["summary"]["latest_regime"] == "BULL TREND"


def test_replay_visualization_scrub_state() -> None:
    payload = build_replay_visualization_payload(
        FakeQuantRepository(),
        replay_run_id="run-1",
        snapshot_date="2026-02-01",
    )
    assert payload["scrub_state"]["regime"] == "BULL TREND"
    assert len(payload["drawdown_curve"]) >= 1


def test_audit_trace_correctness() -> None:
    explanation = explain_signal("audit-1", repository=FakeQuantRepository())
    assert explanation is not None
    steps = [step["step"] for step in explanation["reasoning_chain"]]
    assert steps == ["model_outputs", "calibration", "regime", "meta_model", "guardrails", "final_decision"]


def test_overview_payload_kpis() -> None:
    overview = build_overview_payload(FakeQuantRepository())
    assert overview["kpis"]["active_signals"] >= 1
    assert overview["kpis"]["current_regime"] == "BULL TREND"


def test_dashboard_api_endpoints() -> None:
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: FakeQuantRepository()
    app.dependency_overrides[get_current_user] = lambda: AuthUser(
        id="user-1",
        email="ops@moneymaker.local",
        role="authenticated",
        claims={},
    )
    client = TestClient(app)

    for path in [
        "/dashboard/overview",
        "/dashboard/signals",
        "/dashboard/models",
        "/dashboard/calibration",
        "/dashboard/regimes",
        "/dashboard/replay",
        "/dashboard/risk",
        "/dashboard/notifications",
        "/dashboard/drift",
        "/dashboard/infrastructure",
        "/dashboard/audit",
        "/dashboard/audit/audit-1",
    ]:
        response = client.get(path)
        assert response.status_code == 200, path

    app.dependency_overrides.clear()
