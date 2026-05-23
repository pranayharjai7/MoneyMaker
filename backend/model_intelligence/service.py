from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from statistics import fmean
from typing import Any

from backend.core.math_utils import safe_float
from backend.db.repository import SupabaseRepository
from backend.drift_detection.service import build_drift_report
from backend.quant_dashboard.shared import rolling_series


def _leaderboard(performances: Sequence[Mapping[str, Any]], drift_events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    drift_by_model = {
        str(event.get("model_name")): safe_float(event.get("drift_score"))
        for event in drift_events
        if event.get("model_name")
    }
    rows = []
    for performance in performances:
        model_name = str(performance.get("model_name"))
        rows.append(
            {
                "model": model_name,
                "sharpe": round(safe_float(performance.get("sharpe_contribution")), 4),
                "win_rate": round(safe_float(performance.get("accuracy")), 4),
                "drift": round(drift_by_model.get(model_name, 0.0), 4),
                "calibration_error": round(safe_float(performance.get("calibration_error")), 4),
                "false_positive_rate": round(
                    max(0.0, 1.0 - safe_float(performance.get("accuracy"))), 4
                ),
                "sample_size": int(performance.get("sample_size") or 0),
            }
        )
    return sorted(rows, key=lambda row: row["sharpe"], reverse=True)


def _rolling_performance(outcomes: Sequence[Mapping[str, Any]], window: int = 20) -> dict[str, list[dict[str, Any]]]:
    by_model: dict[str, list[float]] = defaultdict(list)
    for row in sorted(outcomes, key=lambda item: str(item.get("created_at") or item.get("timestamp"))):
        model_name = str(row.get("model_name") or "ensemble")
        label = 1.0 if safe_float(row.get("actual_return")) >= 0 else -1.0
        by_model[model_name].append(label)

    return {
        model_name: rolling_series(values, window)
        for model_name, values in by_model.items()
    }


def build_model_intelligence_payload(
    repository: SupabaseRepository | None = None,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    performances = repository.list_model_performance()
    drift = build_drift_report(repository=repository)
    since = (datetime.now(tz=UTC) - timedelta(days=90)).isoformat()
    outcomes = repository.list_prediction_outcomes(since_timestamp=since)

    return {
        "leaderboard": _leaderboard(performances, drift.get("events", [])),
        "models": performances,
        "rolling_performance": _rolling_performance(outcomes),
        "drift": drift,
        "updated_at": datetime.now(tz=UTC).isoformat(),
    }
