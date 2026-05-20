from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import fmean
from typing import Any

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from backend.core.math_utils import clamp, safe_float
from backend.db.repository import SupabaseRepository


MIN_CALIBRATION_SAMPLES = 8
CALIBRATION_WINDOW_DAYS = 180


@dataclass
class ProbabilityCalibrator:
    model_name: str
    method: str
    sample_size: int
    calibration_error: float
    estimator: Any | None = None
    empirical_rate: float = 0.5

    def predict(self, raw_probability: float) -> float:
        raw_probability = clamp(raw_probability)
        if self.method == "isotonic_regression" and self.estimator is not None:
            return clamp(float(self.estimator.predict([raw_probability])[0]))
        if self.method == "platt_scaling" and self.estimator is not None:
            return clamp(float(self.estimator.predict_proba([[raw_probability]])[0][1]))
        if self.sample_size <= 0:
            return raw_probability
        # Light empirical shrinkage keeps early calibration adaptive without overfitting.
        shrinkage = min(self.sample_size / MIN_CALIBRATION_SAMPLES, 1.0) * 0.35
        return clamp((raw_probability * (1.0 - shrinkage)) + (self.empirical_rate * shrinkage))

    def confidence_interval(self, calibrated_probability: float) -> tuple[float, float]:
        effective_n = max(self.sample_size, 1)
        standard_error = (calibrated_probability * (1.0 - calibrated_probability) / effective_n) ** 0.5
        width = max(0.03, min(0.30, 1.96 * standard_error))
        return clamp(calibrated_probability - width), clamp(calibrated_probability + width)


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


def _calibration_error(probabilities: Sequence[float], labels: Sequence[float], bins: int = 10) -> float:
    if not probabilities:
        return 0.0
    total = len(probabilities)
    error = 0.0
    for bin_index in range(bins):
        lower = bin_index / bins
        upper = (bin_index + 1) / bins
        indices = [
            index
            for index, probability in enumerate(probabilities)
            if lower <= probability < upper or (bin_index == bins - 1 and probability == 1.0)
        ]
        if not indices:
            continue
        mean_probability = fmean(probabilities[index] for index in indices)
        realized_rate = fmean(labels[index] for index in indices)
        error += (len(indices) / total) * abs(mean_probability - realized_rate)
    return error


def _fit_calibrator(model_name: str, rows: Sequence[Mapping[str, Any]]) -> ProbabilityCalibrator:
    probabilities = [clamp(safe_float(row.get("predicted_probability"), 0.5)) for row in rows]
    labels = [1.0 if safe_float(row.get("actual_return")) >= 0 else 0.0 for row in rows]
    sample_size = len(probabilities)
    empirical_rate = fmean(labels) if labels else 0.5
    calibration_error = _calibration_error(probabilities, labels)

    if sample_size >= MIN_CALIBRATION_SAMPLES and len(set(labels)) > 1:
        estimator = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        estimator.fit(np.array(probabilities), np.array(labels))
        return ProbabilityCalibrator(
            model_name=model_name,
            method="isotonic_regression",
            sample_size=sample_size,
            calibration_error=calibration_error,
            estimator=estimator,
            empirical_rate=empirical_rate,
        )

    if sample_size >= 4 and len(set(labels)) > 1:
        estimator = LogisticRegression(solver="liblinear", random_state=42)
        estimator.fit(np.array(probabilities).reshape(-1, 1), np.array(labels))
        return ProbabilityCalibrator(
            model_name=model_name,
            method="platt_scaling",
            sample_size=sample_size,
            calibration_error=calibration_error,
            estimator=estimator,
            empirical_rate=empirical_rate,
        )

    return ProbabilityCalibrator(
        model_name=model_name,
        method="empirical_fallback",
        sample_size=sample_size,
        calibration_error=calibration_error,
        empirical_rate=empirical_rate,
    )


def _fit_calibrators(outcomes: Sequence[Mapping[str, Any]]) -> dict[str, ProbabilityCalibrator]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in outcomes:
        model_name = row.get("model_name")
        if model_name:
            grouped[str(model_name)].append(row)
    return {
        model_name: _fit_calibrator(model_name, model_rows)
        for model_name, model_rows in grouped.items()
    }


def _default_calibrator(model_name: str) -> ProbabilityCalibrator:
    return ProbabilityCalibrator(
        model_name=model_name,
        method="empirical_fallback",
        sample_size=0,
        calibration_error=0.0,
    )


def calibrate_recent_predictions(
    repository: SupabaseRepository | None = None,
    prediction_limit: int = 1000,
    calibration_window_days: int = CALIBRATION_WINDOW_DAYS,
    as_of: datetime | None = None,
) -> dict[str, int]:
    repository = repository or SupabaseRepository()
    as_of = (as_of or datetime.now(tz=UTC)).astimezone(UTC)
    since = as_of - timedelta(days=calibration_window_days)
    outcomes = repository.list_prediction_outcomes(since_timestamp=_iso(since))
    calibrators = _fit_calibrators(outcomes)
    predictions = repository.list_recent_model_predictions(limit=prediction_limit)

    rows = []
    for prediction in predictions:
        prediction_id = prediction.get("id")
        stock_id = prediction.get("stock_id")
        model_name = prediction.get("model_name")
        timestamp = prediction.get("timestamp")
        if not prediction_id or not stock_id or not model_name or not timestamp:
            continue
        raw_probability = clamp(safe_float(prediction.get("probability_up"), 0.5))
        calibrator = calibrators.get(str(model_name), _default_calibrator(str(model_name)))
        calibrated_probability = calibrator.predict(raw_probability)
        interval_low, interval_high = calibrator.confidence_interval(calibrated_probability)
        rows.append(
            {
                "prediction_id": str(prediction_id),
                "model_name": str(model_name),
                "stock_id": str(stock_id),
                "raw_probability": raw_probability,
                "calibrated_probability": calibrated_probability,
                "confidence_interval_low": interval_low,
                "confidence_interval_high": interval_high,
                "calibration_method": calibrator.method,
                "sample_size": calibrator.sample_size,
                "calibration_error": calibrator.calibration_error,
                "timestamp": _iso(_to_utc_datetime(timestamp)),
            }
        )

    stored = repository.upsert_calibrated_predictions(rows)
    return {
        "calibration_models": len(calibrators),
        "calibrated_predictions": len(stored),
    }


def build_calibration_status(
    repository: SupabaseRepository | None = None,
    calibration_window_days: int = CALIBRATION_WINDOW_DAYS,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    as_of = (as_of or datetime.now(tz=UTC)).astimezone(UTC)
    since = as_of - timedelta(days=calibration_window_days)
    outcomes = repository.list_prediction_outcomes(since_timestamp=_iso(since))
    calibrators = _fit_calibrators(outcomes)
    latest_timestamp = repository.latest_calibrated_prediction_timestamp()
    latest_rows = repository.list_calibrated_predictions(limit=500)

    model_names = sorted(
        {
            *calibrators.keys(),
            *{str(row.get("model_name")) for row in latest_rows if row.get("model_name")},
        }
    )
    models = []
    for model_name in model_names:
        calibrator = calibrators.get(model_name)
        latest_for_model = [
            row for row in latest_rows if str(row.get("model_name")) == model_name
        ]
        if calibrator is None and latest_for_model:
            latest = latest_for_model[0]
            calibrator = ProbabilityCalibrator(
                model_name=model_name,
                method=str(latest.get("calibration_method") or "empirical_fallback"),
                sample_size=int(latest.get("sample_size") or 0),
                calibration_error=safe_float(latest.get("calibration_error")),
            )
        if calibrator is None:
            continue
        models.append(
            {
                "model_name": model_name,
                "calibration_method": calibrator.method,
                "sample_size": calibrator.sample_size,
                "calibration_error": calibrator.calibration_error,
            }
        )

    return {
        "status": "ready" if models else "insufficient_feedback",
        "models": models,
        "window_days": calibration_window_days,
        "latest_calibrated_at": latest_timestamp,
    }
