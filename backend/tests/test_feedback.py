from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.feedback.service import build_feedback_summary, evaluate_prediction_outcomes


class FakeFeedbackRepository:
    def __init__(self) -> None:
        self.predictions = [
            {
                "id": "prediction-1",
                "stock_id": "stock-1",
                "timestamp": "2026-05-01T21:00:00+00:00",
                "model_name": "momentum",
                "probability_up": 0.72,
                "expected_return": 0.04,
            }
        ]
        self.prices = [
            {"stock_id": "stock-1", "timestamp": "2026-05-01T21:00:00+00:00", "close": 100.0},
            {"stock_id": "stock-1", "timestamp": "2026-05-02T21:00:00+00:00", "close": 103.0},
            {"stock_id": "stock-1", "timestamp": "2026-05-04T21:00:00+00:00", "close": 106.0},
        ]
        self.outcomes: list[dict[str, Any]] = []
        self.performance: list[dict[str, Any]] = []

    def list_model_predictions_for_feedback(
        self,
        cutoff_timestamp: str,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        return self.predictions[:limit]

    def get_prediction_outcomes_for_prediction_ids(
        self,
        prediction_ids: list[str],
    ) -> list[dict[str, Any]]:
        return [
            {
                "prediction_id": row["prediction_id"],
                "horizon_days": row["horizon_days"],
            }
            for row in self.outcomes
            if row["prediction_id"] in prediction_ids
        ]

    def get_price_at_or_before(self, stock_id: str, timestamp: str) -> dict[str, Any] | None:
        rows = [
            row
            for row in self.prices
            if row["stock_id"] == stock_id and row["timestamp"] <= timestamp
        ]
        return sorted(rows, key=lambda row: row["timestamp"], reverse=True)[0] if rows else None

    def get_price_at_or_after(self, stock_id: str, timestamp: str) -> dict[str, Any] | None:
        rows = [
            row
            for row in self.prices
            if row["stock_id"] == stock_id and row["timestamp"] >= timestamp
        ]
        return sorted(rows, key=lambda row: row["timestamp"])[0] if rows else None

    def upsert_prediction_outcomes(
        self,
        outcomes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        self.outcomes.extend(outcomes)
        return outcomes

    def list_prediction_outcomes(
        self,
        since_timestamp: str | None = None,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        return self.outcomes[:limit]

    def upsert_model_performance(
        self,
        rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        self.performance = rows
        return rows

    def list_model_performance(self) -> list[dict[str, Any]]:
        return self.performance


def test_evaluate_prediction_outcomes_stores_horizon_results_and_metrics() -> None:
    repository = FakeFeedbackRepository()

    result = evaluate_prediction_outcomes(
        repository=repository,
        horizons=(1, 3),
        as_of=datetime(2026, 5, 10, tzinfo=UTC),
    )

    assert result == {"evaluated_predictions": 1, "outcomes": 2, "performance_rows": 1}
    assert repository.outcomes[0]["predicted_direction"] == "up"
    assert repository.outcomes[0]["success"] is True
    assert repository.outcomes[0]["actual_return"] == 0.03
    assert repository.performance[0]["model_name"] == "momentum"
    assert repository.performance[0]["accuracy"] == 1.0


def test_build_feedback_summary_reports_rolling_outcomes() -> None:
    repository = FakeFeedbackRepository()
    evaluate_prediction_outcomes(
        repository=repository,
        horizons=(1, 3),
        as_of=datetime(2026, 5, 10, tzinfo=UTC),
    )

    summary = build_feedback_summary(
        repository=repository,
        as_of=datetime(2026, 5, 10, tzinfo=UTC),
    )

    assert summary["total_outcomes"] == 2
    assert summary["success_rate"] == 1.0
    assert summary["horizons"] == [1, 3]
    assert summary["models_tracked"] == 1
