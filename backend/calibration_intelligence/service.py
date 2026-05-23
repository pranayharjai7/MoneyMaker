from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from backend.calibration.service import _calibration_error, build_calibration_status
from backend.core.math_utils import clamp, safe_float
from backend.db.repository import SupabaseRepository
from backend.quant_dashboard.shared import brier_score, probability_buckets


def _reliability_diagram(outcomes: Sequence[Mapping[str, Any]], bins: int = 10) -> list[dict[str, Any]]:
    rows = [
        {
            "buy_probability": clamp(safe_float(row.get("predicted_probability"), 0.5)),
            "outcome": "win" if safe_float(row.get("actual_return")) >= 0 else "loss",
        }
        for row in outcomes
    ]
    return probability_buckets(rows, bins=bins)


def _brier_timeline(outcomes: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    now = datetime.now(tz=UTC)
    windows = {
        "daily": now - timedelta(days=1),
        "weekly": now - timedelta(days=7),
        "monthly": now - timedelta(days=30),
    }
    result: dict[str, float] = {}
    for label, start in windows.items():
        window_rows = [
            row
            for row in outcomes
            if _parse_ts(row.get("created_at") or row.get("timestamp")) >= start
        ]
        mapped = [
            {
                "buy_probability": clamp(safe_float(row.get("predicted_probability"), 0.5)),
                "outcome": "win" if safe_float(row.get("actual_return")) >= 0 else "loss",
            }
            for row in window_rows
        ]
        result[label] = round(brier_score(mapped), 4) if mapped else 0.0
    return result


def _parse_ts(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value or "")
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        parsed = datetime.fromisoformat(text) if text else datetime.min.replace(tzinfo=UTC)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def build_calibration_intelligence_payload(
    repository: SupabaseRepository | None = None,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    since = (datetime.now(tz=UTC) - timedelta(days=180)).isoformat()
    outcomes = repository.list_prediction_outcomes(since_timestamp=since)
    status = build_calibration_status(repository=repository)

    probabilities = [clamp(safe_float(row.get("predicted_probability"), 0.5)) for row in outcomes]
    labels = [1.0 if safe_float(row.get("actual_return")) >= 0 else 0.0 for row in outcomes]

    return {
        "status": status,
        "reliability_diagram": _reliability_diagram(outcomes),
        "calibration_curve": [
            {"predicted": row["predicted"], "actual": row["actual"], "count": row["count"]}
            for row in _reliability_diagram(outcomes)
            if row["count"] > 0
        ],
        "brier_scores": _brier_timeline(outcomes),
        "aggregate_calibration_error": round(_calibration_error(probabilities, labels), 4),
        "updated_at": datetime.now(tz=UTC).isoformat(),
    }
