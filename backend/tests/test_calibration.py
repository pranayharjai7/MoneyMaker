from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.calibration.service import build_calibration_status, calibrate_recent_predictions


class FakeCalibrationRepository:
    def __init__(self) -> None:
        self.outcomes = [
            {
                "model_name": "momentum",
                "predicted_probability": probability,
                "actual_return": actual_return,
                "timestamp": "2026-05-01T21:00:00+00:00",
            }
            for probability, actual_return in (
                (0.20, -0.04),
                (0.25, -0.02),
                (0.35, -0.01),
                (0.45, 0.01),
                (0.55, -0.01),
                (0.65, 0.02),
                (0.75, 0.03),
                (0.85, 0.05),
            )
        ]
        self.predictions = [
            {
                "id": "prediction-1",
                "stock_id": "stock-1",
                "model_name": "momentum",
                "probability_up": 0.72,
                "timestamp": "2026-05-20T21:00:00+00:00",
            }
        ]
        self.calibrated_rows: list[dict[str, Any]] = []

    def list_prediction_outcomes(
        self,
        since_timestamp: str | None = None,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        return self.outcomes[:limit]

    def list_recent_model_predictions(self, limit: int = 1000) -> list[dict[str, Any]]:
        return self.predictions[:limit]

    def upsert_calibrated_predictions(
        self,
        rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        self.calibrated_rows = rows
        return rows

    def latest_calibrated_prediction_timestamp(self) -> str | None:
        if not self.calibrated_rows:
            return None
        return self.calibrated_rows[0]["timestamp"]

    def list_calibrated_predictions(
        self,
        stock_id: str | None = None,
        timestamp: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        return self.calibrated_rows[:limit]


def test_calibrate_recent_predictions_uses_feedback_and_stores_intervals() -> None:
    repository = FakeCalibrationRepository()

    result = calibrate_recent_predictions(
        repository=repository,
        as_of=datetime(2026, 5, 21, tzinfo=UTC),
    )

    row = repository.calibrated_rows[0]
    assert result == {"calibration_models": 1, "calibrated_predictions": 1}
    assert row["raw_probability"] == 0.72
    assert row["calibration_method"] == "isotonic_regression"
    assert 0 <= row["confidence_interval_low"] <= row["calibrated_probability"]
    assert row["calibrated_probability"] <= row["confidence_interval_high"] <= 1


def test_build_calibration_status_reports_model_readiness() -> None:
    repository = FakeCalibrationRepository()
    calibrate_recent_predictions(
        repository=repository,
        as_of=datetime(2026, 5, 21, tzinfo=UTC),
    )

    status = build_calibration_status(
        repository=repository,
        as_of=datetime(2026, 5, 21, tzinfo=UTC),
    )

    assert status["status"] == "ready"
    assert status["models"][0]["model_name"] == "momentum"
    assert status["models"][0]["sample_size"] == 8
