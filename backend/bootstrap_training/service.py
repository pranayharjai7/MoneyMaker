from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from statistics import fmean, pstdev
from typing import Any

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor

from backend.calibration.service import _fit_calibrators
from backend.core.math_utils import clamp, safe_float
from backend.db.repository import SupabaseRepository
from backend.historical_signals.service import (
    build_calibration_rows_from_replay,
    calibrate_historical_signals,
    walk_forward_calibration_snapshots,
)
from backend.meta_model.service import (
    MetaModel,
    _feature_names,
    _prediction_features,
    _sample_weights,
    _sharpe_score,
)


def _to_utc_datetime(value: Any) -> datetime:
    text = str(value)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text) if not isinstance(value, datetime) else value
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _replay_meta_training_frame(
    signals: list[dict[str, Any]],
    outcomes: list[dict[str, Any]],
    *,
    as_of: datetime,
    window_days: int = 365,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[int], list[str]]:
    since = as_of - timedelta(days=window_days)
    outcomes_by_signal = {str(row["historical_signal_id"]): row for row in outcomes}
    model_names: set[str] = set()
    examples: list[tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]] = []

    for signal in signals:
        signal_time = _to_utc_datetime(signal["timestamp"])
        if signal_time >= as_of or signal_time < since:
            continue
        outcome = outcomes_by_signal.get(str(signal.get("id") or ""))
        if not outcome:
            continue
        exit_time = _to_utc_datetime(outcome.get("exit_timestamp") or signal["timestamp"])
        if exit_time >= as_of:
            continue
        predictions = list(signal.get("model_predictions") or [])
        if not predictions:
            continue
        model_names.update(str(row.get("model_name")) for row in predictions)
        examples.append((signal, predictions, outcome))

    names = _feature_names(model_names)
    feature_rows: list[list[float]] = []
    labels: list[int] = []
    returns: list[float] = []
    horizons: list[int] = []
    for signal, predictions, outcome in examples:
        indicator = {
            "volatility": safe_float(signal.get("risk_score")) * 0.1,
            "volume_momentum": 0.0,
        }
        regime = {"current_regime": signal.get("regime"), "confidence": 0.6}
        feature_rows.append(_prediction_features(predictions, names, indicator, regime))
        actual_return = safe_float(outcome.get("actual_return"))
        labels.append(1 if actual_return >= 0 else 0)
        returns.append(actual_return)
        horizons.append(max(1, int(outcome.get("horizon_days") or signal.get("hold_days") or 1)))

    if not feature_rows:
        return np.array([]), np.array([]), np.array([]), [], names
    return (
        np.array(feature_rows, dtype=float),
        np.array(labels, dtype=int),
        np.array(returns, dtype=float),
        horizons,
        names,
    )


def train_meta_model_from_replay(
    replay_run_id: str,
    *,
    repository: SupabaseRepository | None = None,
    window_days: int = 365,
) -> MetaModel:
    repository = repository or SupabaseRepository()
    signals = repository.list_historical_signals(replay_run_id=replay_run_id, limit=50_000)
    outcomes = repository.list_replay_outcomes(replay_run_id=replay_run_id, limit=50_000)
    as_of = datetime.now(tz=UTC)
    features, labels, returns, horizons, names = _replay_meta_training_frame(
        signals,
        outcomes,
        as_of=as_of,
        window_days=window_days,
    )

    classifier = None
    regressor = None
    model_type = "performance_weighted_fallback"
    sharpe_objective_score = 0.0
    if len(features) >= 20 and len(set(labels.tolist())) > 1:
        weights = _sample_weights(returns.tolist())
        classifier = GradientBoostingClassifier(random_state=42)
        classifier.fit(features, labels, sample_weight=weights)
        regressor = GradientBoostingRegressor(random_state=42)
        regressor.fit(features, returns, sample_weight=weights)
        probabilities = classifier.predict_proba(features)[:, 1].tolist()
        sharpe_objective_score = _sharpe_score(probabilities, returns.tolist(), horizons)
        model_type = "gradient_boosting"

    return MetaModel(
        model_type=model_type,
        feature_names=names,
        classifier=classifier,
        regressor=regressor,
        sharpe_objective_score=sharpe_objective_score,
        sample_size=len(features),
    )


def bootstrap_calibration_training(
    replay_run_id: str,
    *,
    repository: SupabaseRepository | None = None,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    calibrated = calibrate_historical_signals(replay_run_id, repository=repository)
    snapshots = walk_forward_calibration_snapshots(replay_run_id, repository=repository)
    signals = repository.list_historical_signals(replay_run_id=replay_run_id, limit=50_000)
    outcomes = repository.list_replay_outcomes(replay_run_id=replay_run_id, limit=50_000)
    rows = build_calibration_rows_from_replay(signals, outcomes)
    calibrators = _fit_calibrators(rows)
    metrics = {
        **calibrated,
        **snapshots,
        "models": [
            {
                "model_name": name,
                "method": calibrator.method,
                "sample_size": calibrator.sample_size,
                "calibration_error": calibrator.calibration_error,
            }
            for name, calibrator in calibrators.items()
        ],
    }
    repository.insert_bootstrap_training_run(
        replay_run_id=replay_run_id,
        training_type="calibration",
        status="completed",
        metrics=metrics,
    )
    return metrics


def bootstrap_meta_model_training(
    replay_run_id: str,
    *,
    repository: SupabaseRepository | None = None,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    model = train_meta_model_from_replay(replay_run_id, repository=repository)
    metrics = {
        "meta_model_type": model.model_type,
        "sample_size": model.sample_size,
        "sharpe_objective_score": model.sharpe_objective_score,
        "feature_count": len(model.feature_names),
    }
    repository.insert_bootstrap_training_run(
        replay_run_id=replay_run_id,
        training_type="meta_model",
        status="completed",
        metrics=metrics,
        meta_model_version="replay_bootstrap_v1",
    )
    repository.insert_meta_model_training_run(
        {
            "model_type": model.model_type,
            "sample_size": model.sample_size,
            "feature_names": model.feature_names,
            "sharpe_objective_score": model.sharpe_objective_score,
            "training_window_days": 365,
            "updated_at": datetime.now(tz=UTC).isoformat(),
        }
    )
    return metrics


def run_full_bootstrap_training(
    replay_run_id: str,
    *,
    repository: SupabaseRepository | None = None,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    calibration = bootstrap_calibration_training(replay_run_id, repository=repository)
    from backend.historical_regimes.service import analyze_regimes_for_replay

    regime = analyze_regimes_for_replay(replay_run_id, repository=repository)
    meta = bootstrap_meta_model_training(replay_run_id, repository=repository)
    summary = {"calibration": calibration, "regime": regime, "meta_model": meta}
    repository.insert_bootstrap_training_run(
        replay_run_id=replay_run_id,
        training_type="full",
        status="completed",
        metrics=summary,
        meta_model_version="replay_bootstrap_v1",
    )
    return summary
