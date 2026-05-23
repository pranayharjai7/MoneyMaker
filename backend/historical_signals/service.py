from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from backend.calibration.service import _fit_calibrator, _fit_calibrators
from backend.core.math_utils import clamp, safe_float
from backend.db.repository import SupabaseRepository


def _to_utc_datetime(value: Any) -> datetime:
    text = str(value)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text) if not isinstance(value, datetime) else value
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def build_calibration_rows_from_replay(
    signals: list[dict[str, Any]],
    outcomes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Join historical signals with outcomes for per-model calibration training."""
    outcomes_by_signal = {str(row["historical_signal_id"]): row for row in outcomes}
    rows: list[dict[str, Any]] = []
    for signal in signals:
        signal_id = str(signal.get("id") or "")
        outcome = outcomes_by_signal.get(signal_id)
        if not outcome:
            continue
        actual_return = safe_float(outcome.get("actual_return"))
        for prediction in signal.get("model_predictions") or []:
            rows.append(
                {
                    "model_name": str(prediction.get("model_name")),
                    "predicted_probability": clamp(safe_float(prediction.get("probability_up"), 0.5)),
                    "actual_return": actual_return,
                    "timestamp": signal.get("timestamp"),
                    "stock_id": signal.get("stock_id"),
                }
            )
    return rows


def calibrate_historical_signals(
    replay_run_id: str,
    *,
    repository: SupabaseRepository | None = None,
) -> dict[str, int]:
    repository = repository or SupabaseRepository()
    signals = repository.list_historical_signals(replay_run_id=replay_run_id, limit=50_000)
    outcomes = repository.list_replay_outcomes(replay_run_id=replay_run_id, limit=50_000)
    calibration_rows = build_calibration_rows_from_replay(signals, outcomes)
    calibrators = _fit_calibrators(calibration_rows)

    updated = 0
    for signal in signals:
        predictions = signal.get("model_predictions") or []
        if not predictions:
            continue
        weighted = []
        for prediction in predictions:
            model_name = str(prediction.get("model_name"))
            calibrator = calibrators.get(model_name)
            raw = clamp(safe_float(prediction.get("probability_up"), 0.5))
            calibrated = calibrator.predict(raw) if calibrator else raw
            weighted.append((calibrated, safe_float(prediction.get("confidence"), 0.5)))
        total = sum(weight for _, weight in weighted)
        calibrated_probability = (
            sum(value * weight for value, weight in weighted) / total if total > 0 else signal.get("probability")
        )
        repository.update_historical_signal(
            str(signal["id"]),
            calibrated_probability=clamp(safe_float(calibrated_probability, 0.5)),
        )
        updated += 1
    return {"signals_calibrated": updated, "calibration_models": len(calibrators)}


def summarize_historical_signals(
    replay_run_id: str,
    *,
    repository: SupabaseRepository | None = None,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    signals = repository.list_historical_signals(replay_run_id=replay_run_id, limit=50_000)
    if not signals:
        return {"replay_run_id": replay_run_id, "total": 0}

    by_type: dict[str, int] = defaultdict(int)
    by_regime: dict[str, int] = defaultdict(int)
    probabilities: list[float] = []
    for signal in signals:
        by_type[str(signal.get("signal_type") or "neutral")] += 1
        by_regime[str(signal.get("regime") or "UNKNOWN")] += 1
        probabilities.append(safe_float(signal.get("calibrated_probability") or signal.get("probability"), 0.5))

    return {
        "replay_run_id": replay_run_id,
        "total": len(signals),
        "by_signal_type": dict(by_type),
        "by_regime": dict(by_regime),
        "average_probability": sum(probabilities) / len(probabilities),
        "first_timestamp": min(_to_utc_datetime(row["timestamp"]).isoformat() for row in signals),
        "last_timestamp": max(_to_utc_datetime(row["timestamp"]).isoformat() for row in signals),
    }


def walk_forward_calibration_snapshots(
    replay_run_id: str,
    *,
    repository: SupabaseRepository | None = None,
    rebalance_days: int = 30,
) -> dict[str, int]:
    """Sequential calibration snapshots using only prior replay outcomes."""
    repository = repository or SupabaseRepository()
    signals = repository.list_historical_signals(replay_run_id=replay_run_id, limit=50_000)
    outcomes = repository.list_replay_outcomes(replay_run_id=replay_run_id, limit=50_000)
    rows = build_calibration_rows_from_replay(signals, outcomes)
    if not rows:
        return {"snapshots": 0}

    rows.sort(key=lambda row: _to_utc_datetime(row["timestamp"]))
    checkpoints = sorted(
        {
            _to_utc_datetime(row["timestamp"]).date()
            for index, row in enumerate(rows)
            if index > 0 and index % max(1, rebalance_days) == 0
        }
    )
    if not checkpoints:
        checkpoints = [_to_utc_datetime(rows[-1]["timestamp"]).date()]

    stored = 0
    for checkpoint in checkpoints:
        prior = [
            row
            for row in rows
            if _to_utc_datetime(row["timestamp"]).date() < checkpoint
        ]
        if len(prior) < 8:
            continue
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in prior:
            grouped[str(row["model_name"])].append(row)
        snapshots = []
        for model_name, model_rows in grouped.items():
            calibrator = _fit_calibrator(model_name, model_rows)
            snapshots.append(
                {
                    "replay_run_id": replay_run_id,
                    "model_name": model_name,
                    "as_of_date": checkpoint.isoformat(),
                    "calibration_method": calibrator.method,
                    "sample_size": calibrator.sample_size,
                    "calibration_error": calibrator.calibration_error,
                    "empirical_rate": calibrator.empirical_rate,
                }
            )
        stored += len(repository.upsert_historical_calibration_snapshots(snapshots))
    return {"snapshots": stored}
