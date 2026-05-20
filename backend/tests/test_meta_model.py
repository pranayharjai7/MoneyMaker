from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from backend.meta_model.service import generate_meta_model_signals, train_meta_model


class FakeMetaModelRepository:
    def __init__(self) -> None:
        base = datetime(2026, 4, 1, 21, tzinfo=UTC)
        self.outcomes = []
        self.predictions_by_timestamp: dict[str, list[dict[str, Any]]] = {}
        for index in range(10):
            timestamp = (base + timedelta(days=index)).isoformat()
            positive = index % 2 == 0
            actual_return = 0.03 if positive else -0.025
            self.outcomes.append(
                {
                    "stock_id": "stock-1",
                    "timestamp": timestamp,
                    "actual_return": actual_return,
                    "horizon_days": 3,
                }
            )
            self.predictions_by_timestamp[timestamp] = [
                {
                    "id": f"momentum-{index}",
                    "stock_id": "stock-1",
                    "timestamp": timestamp,
                    "model_name": "momentum",
                    "probability_up": 0.72 if positive else 0.28,
                    "expected_return": 0.03 if positive else -0.02,
                    "confidence": 0.8,
                },
                {
                    "id": f"mean-reversion-{index}",
                    "stock_id": "stock-1",
                    "timestamp": timestamp,
                    "model_name": "mean_reversion",
                    "probability_up": 0.62 if positive else 0.38,
                    "expected_return": 0.02 if positive else -0.015,
                    "confidence": 0.7,
                },
            ]
        self.current_timestamp = datetime(2026, 5, 20, 21, tzinfo=UTC).isoformat()
        self.predictions_by_timestamp[self.current_timestamp] = [
            {
                "id": "current-momentum",
                "stock_id": "stock-1",
                "timestamp": self.current_timestamp,
                "model_name": "momentum",
                "probability_up": 0.76,
                "expected_return": 0.04,
                "confidence": 0.82,
            },
            {
                "id": "current-mean-reversion",
                "stock_id": "stock-1",
                "timestamp": self.current_timestamp,
                "model_name": "mean_reversion",
                "probability_up": 0.66,
                "expected_return": 0.025,
                "confidence": 0.72,
            },
        ]
        self.training_runs: list[dict[str, Any]] = []
        self.signals: list[dict[str, Any]] = []

    def list_prediction_outcomes(
        self,
        since_timestamp: str | None = None,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        return self.outcomes[:limit]

    def get_model_predictions(
        self,
        stock_id: str,
        timestamp: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        if timestamp:
            return self.predictions_by_timestamp.get(timestamp, [])[:limit]
        rows = [
            prediction
            for predictions in self.predictions_by_timestamp.values()
            for prediction in predictions
            if prediction["stock_id"] == stock_id
        ]
        return sorted(rows, key=lambda row: row["timestamp"], reverse=True)[:limit]

    def get_indicator_at_or_before(self, stock_id: str, timestamp: str) -> dict[str, Any]:
        return {"volatility": 0.02, "volume_momentum": 0.15}

    def get_market_regime_at_or_before(self, timestamp: str) -> dict[str, Any]:
        return self.latest_market_regime()

    def latest_market_regime(self) -> dict[str, Any]:
        return {
            "current_regime": "BULL TREND",
            "confidence": 0.82,
            "volatility_proxy": 0.16,
            "sector_correlation_shift": 0.02,
        }

    def insert_meta_model_training_run(self, row: dict[str, Any]) -> dict[str, Any]:
        self.training_runs.append(row)
        return row

    def list_stocks(self) -> list[dict[str, Any]]:
        return [{"id": "stock-1", "ticker": "AAPL"}]

    def list_model_performance(self) -> list[dict[str, Any]]:
        return [
            {
                "model_name": "momentum",
                "accuracy": 0.7,
                "brier_score": 0.2,
                "calibration_error": 0.08,
                "sharpe_contribution": 1.1,
            },
            {
                "model_name": "mean_reversion",
                "accuracy": 0.62,
                "brier_score": 0.24,
                "calibration_error": 0.12,
                "sharpe_contribution": 0.7,
            },
        ]

    def list_calibrated_predictions(
        self,
        stock_id: str | None = None,
        timestamp: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        return [
            {
                "prediction_id": "current-momentum",
                "calibrated_probability": 0.70,
            }
        ]

    def upsert_ensemble_signals(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self.signals = rows
        return rows


def test_train_meta_model_uses_learning_based_stacker() -> None:
    repository = FakeMetaModelRepository()

    model = train_meta_model(
        repository=repository,
        as_of=datetime(2026, 5, 21, tzinfo=UTC),
    )

    assert model.model_type == "logistic_regression"
    assert model.sample_size == 10
    assert repository.training_runs[0]["model_type"] == "logistic_regression"


def test_generate_meta_model_signals_stores_probabilistic_signal() -> None:
    repository = FakeMetaModelRepository()

    result = generate_meta_model_signals(repository=repository, stock_ids=["stock-1"])

    assert result["signals"] == 1
    assert result["meta_model_training_samples"] == 10
    assert 0 <= repository.signals[0]["buy_probability"] <= 1
    assert repository.signals[0]["sell_probability"] == 1 - repository.signals[0]["buy_probability"]
    assert repository.signals[0]["signal_type"] in {"buy", "sell", "neutral"}
