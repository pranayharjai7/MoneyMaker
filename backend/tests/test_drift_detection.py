from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from backend.core.config import Settings
from backend.drift_detection import service as drift_service
from backend.drift_detection.service import (
    detect_model_drift,
    model_weight_multipliers_from_events,
    recent_model_weight_multipliers,
)


class FakeDriftRepository:
    def __init__(self) -> None:
        self.as_of = datetime(2026, 5, 21, tzinfo=UTC)
        self.events: list[dict[str, Any]] = []

    def list_prediction_outcomes(
        self,
        since_timestamp: str | None = None,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        return [
            {
                "model_name": "momentum",
                "timestamp": (self.as_of - timedelta(days=day)).isoformat(),
                "success": False,
            }
            for day in range(1, 8)
        ][:limit]

    def list_prediction_outcomes_between(
        self,
        start_timestamp: str,
        end_timestamp: str,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        del start_timestamp, end_timestamp
        return [
            {
                "model_name": "momentum",
                "timestamp": (self.as_of - timedelta(days=day)).isoformat(),
                "success": True,
            }
            for day in range(45, 65)
        ][:limit]

    def list_recent_model_predictions(self, limit: int = 1000) -> list[dict[str, Any]]:
        values = [0.95, 0.05, 0.93, 0.07, 0.91, 0.09]
        return [
            {
                "model_name": "momentum",
                "probability_up": probability,
            }
            for probability in values
        ][:limit]

    def list_recent_indicators(self, limit: int = 1000) -> list[dict[str, Any]]:
        base = datetime(2026, 1, 1, tzinfo=UTC)
        rows = []
        for index in range(80):
            rows.append(
                {
                    "timestamp": (base + timedelta(days=index)).isoformat(),
                    "volatility": 0.02 if index < 56 else 0.18,
                    "volume_momentum": 0.05 if index < 56 else 0.55,
                }
            )
        return rows[:limit]

    def list_model_performance(self) -> list[dict[str, Any]]:
        return [
            {
                "model_name": "momentum",
                "accuracy": 0.31,
                "calibration_error": 0.34,
                "sharpe_contribution": -0.4,
            }
        ]

    def insert_model_drift_events(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self.events = rows
        return rows


def test_detect_model_drift_persists_degradation_event() -> None:
    repository = FakeDriftRepository()
    settings = Settings(
        drift_min_accuracy=0.55,
        drift_min_sharpe_ratio=0.2,
        drift_max_calibration_error=0.15,
        drift_prediction_instability_threshold=0.2,
    )

    result = detect_model_drift(repository=repository, settings=settings, as_of=repository.as_of)

    assert result["models_checked"] == 1
    assert result["drift_events"] == 1
    assert repository.events[0]["model_name"] == "momentum"
    assert repository.events[0]["severity"] in {"medium", "high", "critical"}
    assert repository.events[0]["metadata"]["recommended_action"] != "monitor"


def test_model_weight_multipliers_disable_critical_models() -> None:
    multipliers = model_weight_multipliers_from_events(
        [
            {"model_name": "momentum", "severity": "critical"},
            {"severity": "medium"},
        ]
    )

    assert multipliers["momentum"] == 0.0


def test_drift_helper_branches_cover_stable_models() -> None:
    settings = Settings(drift_min_accuracy=0.55)

    assert drift_service._to_utc_datetime(datetime(2026, 5, 21)).tzinfo is UTC
    assert drift_service._to_utc_datetime("2026-05-21T00:00:00Z").tzinfo is not None
    assert drift_service._severity(0.7) == "high"
    assert drift_service._severity(0.5) == "medium"
    assert drift_service._severity(0.1) == "low"
    assert drift_service._recommended_action("high") == "reduce_ensemble_weight_and_trigger_retraining"
    assert drift_service._recommended_action("medium") == "reduce_ensemble_weight"
    assert drift_service._recommended_action("low") == "monitor"
    assert drift_service._component_type({}) == "unknown"
    assert drift_service._accuracy([]) == 0.0
    assert drift_service._prediction_instability("momentum", {}) == 0.0
    assert drift_service._feature_drift_score([]) == 0.0
    assert (
        drift_service._accuracy_degradation(
            "momentum",
            {"momentum": [{"success": False}]},
            {},
            settings,
        )
        > 0
    )
    assert (
        drift_service.assess_model_drift(
            {},
            recent_by_model={},
            baseline_by_model={},
            predictions_by_model={},
            feature_drift=0.0,
            settings=settings,
        )
        is None
    )
    assert (
        drift_service.assess_model_drift(
            {
                "model_name": "stable",
                "accuracy": 0.8,
                "calibration_error": 0.01,
                "sharpe_contribution": 1.0,
            },
            recent_by_model={},
            baseline_by_model={},
            predictions_by_model={},
            feature_drift=0.0,
            settings=settings,
        )
        is None
    )


def test_recent_model_weight_multipliers_reads_repository_events() -> None:
    class Repository:
        def list_recent_model_drift_events(self, since_timestamp: str | None = None, limit: int = 500):
            assert since_timestamp is not None
            assert limit == 500
            return [{"model_name": "momentum", "severity": "high"}]

    multipliers = recent_model_weight_multipliers(
        Repository(),
        as_of=datetime(2026, 5, 21, tzinfo=UTC),
    )

    assert multipliers["momentum"] == 0.3
