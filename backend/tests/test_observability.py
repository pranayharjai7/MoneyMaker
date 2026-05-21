from __future__ import annotations

from backend.core.config import Settings
from backend.observability.metrics import MetricsRegistry
from backend.observability.service import (
    models_health,
    notifications_health,
    realtime_health,
    system_health,
)


class FakeHealthRepository:
    def __init__(self, fail_stocks: bool = False) -> None:
        self.fail_stocks = fail_stocks

    def list_stocks(self):
        if self.fail_stocks:
            raise RuntimeError("supabase down")
        return [{"id": "stock-1"}]

    def list_model_performance(self):
        return [{"model_name": "momentum"}]

    def list_recent_model_drift_events(
        self,
        since_timestamp: str | None = None,
        limit: int = 100,
    ):
        return [
            {"model_name": "momentum", "severity": "critical"},
            {"model_name": "mean_reversion", "severity": "medium"},
        ][:limit]

    def list_signals(self, limit: int = 1):
        return [{"timestamp": "2026-05-21T21:00:00+00:00"}][:limit]

    def list_recent_notification_events(
        self,
        status: str | None = None,
        limit: int = 100,
    ):
        rows = [
            {"status": "pending", "created_at": "2026-05-21T21:00:00+00:00"},
            {"status": "sent", "created_at": "2026-05-21T21:00:00+00:00"},
            {"status": "failed", "created_at": "2026-05-21T21:00:00+00:00"},
        ]
        if status:
            rows = [row for row in rows if row["status"] == status]
        return rows[:limit]


def test_metrics_registry_tracks_counters_histograms_and_prunes() -> None:
    registry = MetricsRegistry()

    registry.increment("signal_generation_latency")
    for index in range(1002):
        registry.observe("api_latency_ms", float(index))
    snapshot = registry.snapshot()

    assert snapshot["counters"]["signal_generation_latency"] == 1.0
    assert snapshot["histograms"]["api_latency_ms"]["count"] == 1000
    assert snapshot["histograms"]["api_latency_ms"]["p95"] > 900


def test_health_services_report_degraded_and_ok_components() -> None:
    repository = FakeHealthRepository()

    system = system_health(repository=repository, settings=Settings(redis_url="redis://localhost:6379/0"))
    degraded_system = system_health(repository=FakeHealthRepository(fail_stocks=True), settings=Settings())
    models = models_health(repository=repository)
    realtime = realtime_health(repository=repository)
    notifications = notifications_health(repository=repository)

    assert system["status"] == "ok"
    assert degraded_system["status"] == "degraded"
    assert models["status"] == "degraded"
    assert models["critical_models"] == ["momentum"]
    assert realtime["status"] == "ok"
    assert notifications["pending"] == 1
    assert notifications["delivery_success_rate"] == 0.5
