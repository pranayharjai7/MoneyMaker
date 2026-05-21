from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from backend.signal_quality import service as quality_service
from backend.signal_quality.service import build_signal_quality_report, evaluate_live_signal_quality


class FakeSignalQualityRepository:
    def __init__(self) -> None:
        base = datetime(2026, 5, 1, 21, tzinfo=UTC)
        self.signals = [
            {
                "id": "signal-1",
                "stock_id": "stock-1",
                "timestamp": base.isoformat(),
                "signal_type": "buy",
                "buy_probability": 0.74,
                "sell_probability": 0.26,
                "expected_return": 0.04,
            },
            {
                "id": "signal-2",
                "stock_id": "stock-1",
                "timestamp": (base + timedelta(days=1)).isoformat(),
                "signal_type": "sell",
                "buy_probability": 0.28,
                "sell_probability": 0.72,
                "expected_return": -0.03,
            },
        ]
        self.prices = [
            {"stock_id": "stock-1", "timestamp": base.isoformat(), "close": 100.0},
            {
                "stock_id": "stock-1",
                "timestamp": (base + timedelta(days=1)).isoformat(),
                "close": 102.0,
            },
            {
                "stock_id": "stock-1",
                "timestamp": (base + timedelta(days=5)).isoformat(),
                "close": 106.0,
            },
            {
                "stock_id": "stock-1",
                "timestamp": (base + timedelta(days=6)).isoformat(),
                "close": 98.0,
            },
        ]
        self.live_rows: list[dict[str, Any]] = []
        self.regime_rows: list[dict[str, Any]] = []

    def list_signals_for_quality(self, cutoff_timestamp: str, limit: int = 1000) -> list[dict[str, Any]]:
        return [row for row in self.signals if row["timestamp"] <= cutoff_timestamp][:limit]

    def get_price_at_or_before(self, stock_id: str, timestamp: str) -> dict[str, Any] | None:
        rows = [
            row
            for row in self.prices
            if row["stock_id"] == stock_id and row["timestamp"] <= timestamp
        ]
        return rows[-1] if rows else None

    def get_price_at_or_after(self, stock_id: str, timestamp: str) -> dict[str, Any] | None:
        rows = [
            row
            for row in self.prices
            if row["stock_id"] == stock_id and row["timestamp"] >= timestamp
        ]
        return rows[0] if rows else None

    def latest_meta_model_training_run(self) -> dict[str, Any]:
        return {"model_type": "momentum"}

    def get_market_regime_at_or_before(self, timestamp: str) -> dict[str, Any]:
        return {"current_regime": "BULL TREND"}

    def latest_market_regime(self) -> dict[str, Any]:
        return {"current_regime": "BULL TREND"}

    def upsert_live_signal_performance(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self.live_rows = rows
        return rows

    def list_live_signal_performance(self, limit: int = 1000) -> list[dict[str, Any]]:
        return self.live_rows[:limit]

    def upsert_model_regime_performance(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self.regime_rows = rows
        return rows

    def list_model_regime_performance(self) -> list[dict[str, Any]]:
        return self.regime_rows


def test_evaluate_live_signal_quality_tracks_regime_performance() -> None:
    repository = FakeSignalQualityRepository()

    result = evaluate_live_signal_quality(
        repository=repository,
        horizon_days=5,
        as_of=datetime(2026, 5, 10, tzinfo=UTC),
    )
    report = build_signal_quality_report(repository=repository)

    assert result["live_signal_performance"] == 2
    assert result["model_regime_performance"] == 1
    assert report["summary"]["win_rate"] == 1.0
    assert report["best_models_by_regime"]["BULL TREND"]["model_name"] == "momentum"


def test_signal_quality_helper_branches_handle_inferred_and_missing_data() -> None:
    repository = FakeSignalQualityRepository()
    signal_time = datetime(2026, 5, 1, 21, tzinfo=UTC)

    assert quality_service._to_utc_datetime(signal_time) == signal_time
    assert quality_service._to_utc_datetime("2026-05-01T21:00:00Z").tzinfo is not None
    assert quality_service._to_utc_datetime("2026-05-01T21:00:00").tzinfo is UTC
    assert (
        quality_service._direction(
            {"buy_probability": 0.8, "sell_probability": 0.2, "expected_return": 0.03}
        )
        == "buy"
    )
    assert (
        quality_service._direction(
            {"buy_probability": 0.2, "sell_probability": 0.8, "expected_return": -0.03}
        )
        == "sell"
    )
    assert quality_service._direction({"expected_return": 0.0}) == "neutral"
    assert quality_service._pnl({"signal_type": "neutral"}, 0.1) < 0
    assert quality_service._outcome(-0.1) == "loss"
    assert quality_service._outcome(0.0) == "flat"
    assert quality_service._model_used(repository, {"model_used": "breakout"}) == "breakout"

    repository.latest_meta_model_training_run = lambda: None  # type: ignore[method-assign]
    assert quality_service._model_used(repository, {}) == "meta_model_ensemble"
    assert (
        quality_service._live_performance_row(
            repository,
            {"id": "missing-stock", "timestamp": signal_time.isoformat()},
            horizon_days=5,
        )
        is None
    )
    assert quality_service._sharpe_ratio([0.01], horizon_days=5) == 0.0
    assert quality_service._profit_factor([0.03, -0.01]) == 3.0


def test_signal_quality_uses_stored_rows_when_repository_has_no_history() -> None:
    class Repository(FakeSignalQualityRepository):
        def list_live_signal_performance(self, limit: int = 1000) -> list[dict[str, Any]]:
            return []

    repository = Repository()

    result = evaluate_live_signal_quality(
        repository=repository,
        horizon_days=5,
        as_of=datetime(2026, 5, 10, tzinfo=UTC),
    )

    assert result["model_regime_performance"] == 1
