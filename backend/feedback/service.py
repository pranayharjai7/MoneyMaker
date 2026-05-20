from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import fmean, pstdev
from typing import Any

import math

from backend.core.math_utils import clamp, safe_float
from backend.db.repository import SupabaseRepository


DEFAULT_HORIZONS = (1, 3, 5, 10)
ROLLING_PERFORMANCE_DAYS = 90


@dataclass(frozen=True)
class PredictionTrace:
    prediction_id: str
    stock_id: str
    timestamp: datetime
    predicted_probability: float
    expected_return: float
    predicted_direction: str
    model_used: str


def _to_utc_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value)
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _predicted_direction(probability_up: float, expected_return: float) -> str:
    if expected_return > 0:
        return "up"
    if expected_return < 0:
        return "down"
    if probability_up > 0.55:
        return "up"
    if probability_up < 0.45:
        return "down"
    return "neutral"


def _trace_from_prediction(row: Mapping[str, Any]) -> PredictionTrace | None:
    prediction_id = row.get("id")
    stock_id = row.get("stock_id")
    timestamp = row.get("timestamp")
    model_name = row.get("model_name")
    if not prediction_id or not stock_id or not timestamp or not model_name:
        return None

    probability_up = clamp(safe_float(row.get("probability_up"), 0.5))
    expected_return = safe_float(row.get("expected_return"))
    return PredictionTrace(
        prediction_id=str(prediction_id),
        stock_id=str(stock_id),
        timestamp=_to_utc_datetime(timestamp),
        predicted_probability=probability_up,
        expected_return=expected_return,
        predicted_direction=_predicted_direction(probability_up, expected_return),
        model_used=str(model_name),
    )


def _close(row: Mapping[str, Any] | None) -> float:
    return safe_float((row or {}).get("close"))


def _success(predicted_direction: str, actual_return: float) -> bool:
    if predicted_direction == "down":
        return actual_return <= 0
    if predicted_direction == "neutral":
        return abs(actual_return) < 0.0025
    return actual_return >= 0


def _outcome_row(
    trace: PredictionTrace,
    horizon_days: int,
    entry_close: float,
    exit_close: float,
) -> dict[str, Any]:
    actual_return = (exit_close - entry_close) / entry_close
    error = actual_return - trace.expected_return
    return {
        "stock_id": trace.stock_id,
        "prediction_id": trace.prediction_id,
        "timestamp": _iso(trace.timestamp),
        "horizon_days": horizon_days,
        "model_name": trace.model_used,
        "predicted_probability": trace.predicted_probability,
        "predicted_return": trace.expected_return,
        "predicted_direction": trace.predicted_direction,
        "actual_return": actual_return,
        "error": error,
        "success": _success(trace.predicted_direction, actual_return),
    }


def evaluate_prediction_outcomes(
    repository: SupabaseRepository | None = None,
    horizons: Sequence[int] = DEFAULT_HORIZONS,
    limit: int = 1000,
    as_of: datetime | None = None,
    rolling_days: int = ROLLING_PERFORMANCE_DAYS,
) -> dict[str, int]:
    """Evaluate mature model predictions against realized future closes."""

    repository = repository or SupabaseRepository()
    as_of = (as_of or datetime.now(tz=UTC)).astimezone(UTC)
    clean_horizons = tuple(sorted({int(horizon) for horizon in horizons if int(horizon) > 0}))
    if not clean_horizons:
        return {"evaluated_predictions": 0, "outcomes": 0, "performance_rows": 0}

    cutoff = as_of - timedelta(days=min(clean_horizons))
    prediction_rows = repository.list_model_predictions_for_feedback(_iso(cutoff), limit=limit)
    traces = [trace for row in prediction_rows if (trace := _trace_from_prediction(row))]
    existing_rows = repository.get_prediction_outcomes_for_prediction_ids(
        [trace.prediction_id for trace in traces]
    )
    existing_keys = {
        (str(row.get("prediction_id")), int(row.get("horizon_days", 0)))
        for row in existing_rows
        if row.get("prediction_id") and row.get("horizon_days")
    }

    outcomes: list[dict[str, Any]] = []
    for trace in traces:
        entry_price = repository.get_price_at_or_before(trace.stock_id, _iso(trace.timestamp))
        entry_close = _close(entry_price)
        if entry_close <= 0:
            continue

        for horizon_days in clean_horizons:
            if (trace.prediction_id, horizon_days) in existing_keys:
                continue
            target_time = trace.timestamp + timedelta(days=horizon_days)
            if target_time > as_of:
                continue
            exit_price = repository.get_price_at_or_after(trace.stock_id, _iso(target_time))
            exit_close = _close(exit_price)
            if exit_close <= 0:
                continue
            outcomes.append(_outcome_row(trace, horizon_days, entry_close, exit_close))

    stored_outcomes = repository.upsert_prediction_outcomes(outcomes)
    performance_rows = refresh_model_performance(
        repository=repository,
        rolling_days=rolling_days,
        as_of=as_of,
    )
    return {
        "evaluated_predictions": len(traces),
        "outcomes": len(stored_outcomes),
        "performance_rows": len(performance_rows),
    }


def _expected_calibration_error(rows: Sequence[Mapping[str, Any]], bins: int = 10) -> float:
    if not rows:
        return 0.0

    total = len(rows)
    error = 0.0
    for bin_index in range(bins):
        lower = bin_index / bins
        upper = (bin_index + 1) / bins
        bucket = [
            row
            for row in rows
            if lower <= clamp(safe_float(row.get("predicted_probability"), 0.5)) < upper
            or (bin_index == bins - 1 and safe_float(row.get("predicted_probability")) == 1.0)
        ]
        if not bucket:
            continue
        mean_probability = fmean(
            clamp(safe_float(row.get("predicted_probability"), 0.5)) for row in bucket
        )
        realized_frequency = fmean(1.0 if safe_float(row.get("actual_return")) >= 0 else 0.0 for row in bucket)
        error += (len(bucket) / total) * abs(mean_probability - realized_frequency)
    return error


def _sharpe_contribution(rows: Sequence[Mapping[str, Any]]) -> float:
    directional_returns = []
    horizons = []
    for row in rows:
        actual_return = safe_float(row.get("actual_return"))
        direction = str(row.get("predicted_direction") or "up")
        if direction == "down":
            directional_returns.append(-actual_return)
        elif direction == "neutral":
            directional_returns.append(0.0)
        else:
            directional_returns.append(actual_return)
        horizons.append(max(1, int(row.get("horizon_days") or 1)))

    if len(directional_returns) < 2:
        return 0.0
    volatility = pstdev(directional_returns)
    if volatility <= 0:
        return 0.0
    annualizer = math.sqrt(252.0 / fmean(horizons))
    return (fmean(directional_returns) / volatility) * annualizer


def _performance_rows(
    outcomes: Iterable[Mapping[str, Any]],
    updated_at: datetime,
    rolling_days: int,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in outcomes:
        model_name = row.get("model_name")
        if model_name:
            grouped[str(model_name)].append(row)

    rows = []
    for model_name, model_rows in grouped.items():
        successes = sum(1 for row in model_rows if bool(row.get("success")))
        actual_up = [1.0 if safe_float(row.get("actual_return")) >= 0 else 0.0 for row in model_rows]
        probabilities = [
            clamp(safe_float(row.get("predicted_probability"), 0.5)) for row in model_rows
        ]
        brier_score = fmean(
            (probability - outcome) ** 2
            for probability, outcome in zip(probabilities, actual_up, strict=True)
        )
        rows.append(
            {
                "model_name": model_name,
                "accuracy": clamp(successes / len(model_rows)),
                "brier_score": max(0.0, brier_score),
                "calibration_error": max(0.0, _expected_calibration_error(model_rows)),
                "sharpe_contribution": safe_float(_sharpe_contribution(model_rows)),
                "sample_size": len(model_rows),
                "window_days": rolling_days,
                "updated_at": _iso(updated_at),
            }
        )
    return rows


def refresh_model_performance(
    repository: SupabaseRepository | None = None,
    rolling_days: int = ROLLING_PERFORMANCE_DAYS,
    as_of: datetime | None = None,
) -> list[dict[str, Any]]:
    repository = repository or SupabaseRepository()
    as_of = (as_of or datetime.now(tz=UTC)).astimezone(UTC)
    since = as_of - timedelta(days=rolling_days)
    outcomes = repository.list_prediction_outcomes(since_timestamp=_iso(since))
    rows = _performance_rows(outcomes, updated_at=as_of, rolling_days=rolling_days)
    return repository.upsert_model_performance(rows)


def build_feedback_summary(
    repository: SupabaseRepository | None = None,
    rolling_days: int = ROLLING_PERFORMANCE_DAYS,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    as_of = (as_of or datetime.now(tz=UTC)).astimezone(UTC)
    since = as_of - timedelta(days=rolling_days)
    outcomes = repository.list_prediction_outcomes(since_timestamp=_iso(since))
    performances = repository.list_model_performance()
    total = len(outcomes)
    successes = sum(1 for row in outcomes if bool(row.get("success")))
    errors = [safe_float(row.get("error")) for row in outcomes]
    latest_timestamp = max((_to_utc_datetime(row["timestamp"]) for row in outcomes), default=None)

    return {
        "total_outcomes": total,
        "success_rate": clamp(successes / total) if total else 0.0,
        "average_error": fmean(errors) if errors else 0.0,
        "average_absolute_error": fmean(abs(error) for error in errors) if errors else 0.0,
        "horizons": sorted({int(row.get("horizon_days") or 0) for row in outcomes}),
        "models_tracked": len(performances),
        "window_days": rolling_days,
        "latest_evaluated_at": _iso(latest_timestamp) if latest_timestamp else None,
    }
