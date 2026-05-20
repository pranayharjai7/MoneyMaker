from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import fmean, pstdev
from typing import Any

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression

from backend.core.math_utils import clamp, safe_float
from backend.db.repository import SupabaseRepository


REGIME_STATES = (
    "BULL TREND",
    "BEAR TREND",
    "SIDEWAYS",
    "HIGH VOLATILITY",
    "LOW LIQUIDITY",
)
TRAINING_WINDOW_DAYS = 365


@dataclass(frozen=True)
class MetaModel:
    model_type: str
    feature_names: list[str]
    classifier: Any | None
    regressor: Any | None
    sharpe_objective_score: float
    sample_size: int


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


def _regime_feature_name(regime: str) -> str:
    return f"regime_{regime.lower().replace(' ', '_')}"


def _feature_names(model_names: Iterable[str]) -> list[str]:
    names = []
    for model_name in sorted(set(model_names)):
        names.extend(
            [
                f"probability_{model_name}",
                f"expected_return_{model_name}",
                f"confidence_{model_name}",
            ]
        )
    names.extend(_regime_feature_name(regime) for regime in REGIME_STATES)
    names.extend(
        [
            "regime_confidence",
            "market_volatility",
            "sector_correlation_shift",
            "volatility",
            "volume_momentum",
        ]
    )
    return names


def _performance_by_model(repository: SupabaseRepository) -> dict[str, dict[str, Any]]:
    return {str(row["model_name"]): row for row in repository.list_model_performance()}


def _prediction_features(
    predictions: Sequence[Mapping[str, Any]],
    feature_names: Sequence[str],
    indicator: Mapping[str, Any] | None,
    regime: Mapping[str, Any] | None,
    calibrated_by_prediction_id: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[float]:
    calibrated_by_prediction_id = calibrated_by_prediction_id or {}
    values = {name: 0.0 for name in feature_names}
    for prediction in predictions:
        model_name = str(prediction.get("model_name"))
        prediction_id = str(prediction.get("id") or "")
        calibrated = calibrated_by_prediction_id.get(prediction_id)
        probability = (
            safe_float(calibrated.get("calibrated_probability"), 0.5)
            if calibrated
            else safe_float(prediction.get("probability_up"), 0.5)
        )
        values[f"probability_{model_name}"] = clamp(probability)
        values[f"expected_return_{model_name}"] = safe_float(prediction.get("expected_return"))
        values[f"confidence_{model_name}"] = clamp(safe_float(prediction.get("confidence"), 0.5))

    current_regime = str((regime or {}).get("current_regime") or "SIDEWAYS")
    values[_regime_feature_name(current_regime)] = 1.0
    values["regime_confidence"] = clamp(safe_float((regime or {}).get("confidence"), 0.0))
    values["market_volatility"] = safe_float((regime or {}).get("volatility_proxy"))
    values["sector_correlation_shift"] = safe_float((regime or {}).get("sector_correlation_shift"))
    values["volatility"] = safe_float((indicator or {}).get("volatility"))
    values["volume_momentum"] = safe_float((indicator or {}).get("volume_momentum"))
    return [safe_float(values.get(name)) for name in feature_names]


def _sharpe_score(probabilities: Sequence[float], actual_returns: Sequence[float], horizons: Sequence[int]) -> float:
    if len(probabilities) < 2:
        return 0.0
    strategy_returns = [
        actual_return if probability >= 0.5 else -actual_return
        for probability, actual_return in zip(probabilities, actual_returns, strict=True)
    ]
    volatility = pstdev(strategy_returns)
    if volatility <= 0:
        return 0.0
    annualizer = float(np.sqrt(252.0 / max(fmean(horizons), 1.0)))
    return safe_float((fmean(strategy_returns) / volatility) * annualizer)


def _sample_weights(actual_returns: Sequence[float]) -> np.ndarray:
    if not actual_returns:
        return np.array([])
    volatility = pstdev(actual_returns) if len(actual_returns) > 1 else 0.0
    if volatility <= 0:
        return np.ones(len(actual_returns))
    return np.array([1.0 + min(abs(value) / volatility, 5.0) for value in actual_returns])


def _training_frame(
    repository: SupabaseRepository,
    window_days: int,
    as_of: datetime,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[int], list[str]]:
    since = as_of - timedelta(days=window_days)
    outcomes = repository.list_prediction_outcomes(since_timestamp=_iso(since))
    examples = []
    model_names = set()
    for outcome in outcomes:
        stock_id = str(outcome.get("stock_id") or "")
        timestamp = str(outcome.get("timestamp") or "")
        if not stock_id or not timestamp:
            continue
        predictions = repository.get_model_predictions(stock_id, timestamp=timestamp, limit=50)
        if not predictions:
            continue
        model_names.update(str(prediction.get("model_name")) for prediction in predictions)
        examples.append((outcome, predictions))

    names = _feature_names(model_names)
    feature_rows = []
    labels = []
    returns = []
    horizons = []
    for outcome, predictions in examples:
        stock_id = str(outcome["stock_id"])
        timestamp = str(outcome["timestamp"])
        indicator = repository.get_indicator_at_or_before(stock_id, timestamp)
        regime = repository.get_market_regime_at_or_before(timestamp) or repository.latest_market_regime()
        feature_rows.append(_prediction_features(predictions, names, indicator, regime))
        actual_return = safe_float(outcome.get("actual_return"))
        labels.append(1 if actual_return >= 0 else 0)
        returns.append(actual_return)
        horizons.append(max(1, int(outcome.get("horizon_days") or 1)))

    if not feature_rows:
        return np.array([]), np.array([]), np.array([]), [], names
    return (
        np.array(feature_rows, dtype=float),
        np.array(labels, dtype=int),
        np.array(returns, dtype=float),
        horizons,
        names,
    )


def train_meta_model(
    repository: SupabaseRepository | None = None,
    window_days: int = TRAINING_WINDOW_DAYS,
    as_of: datetime | None = None,
    persist: bool = True,
) -> MetaModel:
    repository = repository or SupabaseRepository()
    as_of = (as_of or datetime.now(tz=UTC)).astimezone(UTC)
    features, labels, returns, horizons, names = _training_frame(repository, window_days, as_of)
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
    elif len(features) >= 8 and len(set(labels.tolist())) > 1:
        weights = _sample_weights(returns.tolist())
        classifier = LogisticRegression(solver="liblinear", random_state=42)
        classifier.fit(features, labels, sample_weight=weights)
        probabilities = classifier.predict_proba(features)[:, 1].tolist()
        sharpe_objective_score = _sharpe_score(probabilities, returns.tolist(), horizons)
        model_type = "logistic_regression"

    model = MetaModel(
        model_type=model_type,
        feature_names=names,
        classifier=classifier,
        regressor=regressor,
        sharpe_objective_score=sharpe_objective_score,
        sample_size=len(features),
    )
    if persist:
        repository.insert_meta_model_training_run(
            {
                "model_type": model.model_type,
                "sample_size": model.sample_size,
                "feature_names": model.feature_names,
                "sharpe_objective_score": model.sharpe_objective_score,
                "training_window_days": window_days,
                "updated_at": _iso(as_of),
            }
        )
    return model


def _adaptive_model_weight(prediction: Mapping[str, Any], performance: Mapping[str, Any] | None) -> float:
    confidence = clamp(safe_float(prediction.get("confidence"), 0.5))
    probability_edge = abs(clamp(safe_float(prediction.get("probability_up"), 0.5)) - 0.5) * 2.0
    if performance:
        accuracy = clamp(safe_float(performance.get("accuracy"), 0.5))
        brier = max(0.0, safe_float(performance.get("brier_score"), 0.25))
        calibration_error = max(0.0, safe_float(performance.get("calibration_error"), 0.25))
        sharpe = safe_float(performance.get("sharpe_contribution"))
        quality = accuracy * max(0.0, 1.0 - brier) * max(0.0, 1.0 - calibration_error)
        return max(0.0001, confidence * (0.25 + probability_edge) * quality * (1.0 + max(sharpe, 0.0)))
    return max(0.0001, confidence * (0.25 + probability_edge))


def _fallback_buy_probability(
    predictions: Sequence[Mapping[str, Any]],
    performances: Mapping[str, Mapping[str, Any]],
) -> float:
    weighted = []
    for prediction in predictions:
        model_name = str(prediction.get("model_name"))
        weight = _adaptive_model_weight(prediction, performances.get(model_name))
        weighted.append((clamp(safe_float(prediction.get("probability_up"), 0.5)), weight))
    total_weight = sum(weight for _, weight in weighted)
    if total_weight <= 0:
        return 0.5
    return clamp(sum(probability * weight for probability, weight in weighted) / total_weight)


def _fallback_expected_return(
    predictions: Sequence[Mapping[str, Any]],
    performances: Mapping[str, Mapping[str, Any]],
) -> float:
    weighted = []
    for prediction in predictions:
        model_name = str(prediction.get("model_name"))
        weight = _adaptive_model_weight(prediction, performances.get(model_name))
        weighted.append((safe_float(prediction.get("expected_return")), weight))
    total_weight = sum(weight for _, weight in weighted)
    if total_weight <= 0:
        return 0.0
    return safe_float(sum(value * weight for value, weight in weighted) / total_weight)


def _risk_score(
    buy_probability: float,
    indicator: Mapping[str, Any] | None,
    regime: Mapping[str, Any] | None,
) -> float:
    uncertainty = 1.0 - abs(buy_probability - 0.5) * 2.0
    volatility = min(safe_float((indicator or {}).get("volatility")) * 6.0, 1.0)
    regime_name = str((regime or {}).get("current_regime") or "")
    regime_risk = 0.0
    if regime_name in {"HIGH VOLATILITY", "LOW LIQUIDITY", "BEAR TREND"}:
        regime_risk = clamp(safe_float((regime or {}).get("confidence"), 0.5))
    return clamp(uncertainty * 0.45 + volatility * 0.30 + regime_risk * 0.25)


def _signal_type(buy_probability: float, expected_return: float) -> str:
    sell_probability = 1.0 - buy_probability
    if buy_probability >= 0.65 and expected_return > 0:
        return "buy"
    if sell_probability >= 0.65 and expected_return < 0:
        return "sell"
    return "neutral"


def _suggested_hold_days(risk_score: float, regime: Mapping[str, Any] | None) -> int:
    if str((regime or {}).get("current_regime")) == "HIGH VOLATILITY":
        return 2
    if risk_score < 0.35:
        return 10
    if risk_score < 0.55:
        return 5
    return 2


def _latest_predictions(
    repository: SupabaseRepository,
    stock_id: str,
) -> tuple[str | None, list[dict[str, Any]]]:
    predictions = repository.get_model_predictions(stock_id, limit=50)
    if not predictions:
        return None, []
    latest_timestamp = max(_to_utc_datetime(row["timestamp"]) for row in predictions)
    latest_rows = [
        row for row in predictions if _to_utc_datetime(row["timestamp"]) == latest_timestamp
    ]
    return _iso(latest_timestamp), latest_rows


def _calibrated_by_prediction_id(
    repository: SupabaseRepository,
    stock_id: str,
) -> dict[str, dict[str, Any]]:
    rows = repository.list_calibrated_predictions(stock_id=stock_id, limit=100)
    return {str(row["prediction_id"]): row for row in rows if row.get("prediction_id")}


def generate_meta_model_signals(
    repository: SupabaseRepository | None = None,
    stock_ids: Iterable[str] | None = None,
    window_days: int = TRAINING_WINDOW_DAYS,
) -> dict[str, int]:
    repository = repository or SupabaseRepository()
    if stock_ids is None:
        stock_ids = [stock["id"] for stock in repository.list_stocks()]

    meta_model = train_meta_model(repository=repository, window_days=window_days)
    performances = _performance_by_model(repository)
    rows = []
    for stock_id in stock_ids:
        timestamp, predictions = _latest_predictions(repository, stock_id)
        if not timestamp or not predictions:
            continue
        indicator = repository.get_indicator_at_or_before(stock_id, timestamp)
        regime = repository.latest_market_regime()
        calibrated = _calibrated_by_prediction_id(repository, stock_id)
        if meta_model.feature_names:
            features = np.array(
                [_prediction_features(predictions, meta_model.feature_names, indicator, regime, calibrated)],
                dtype=float,
            )
        else:
            features = np.array([])

        if meta_model.classifier is not None and len(features):
            buy_probability = clamp(float(meta_model.classifier.predict_proba(features)[0][1]))
        else:
            enriched_predictions = [
                {
                    **prediction,
                    "probability_up": safe_float(
                        calibrated.get(str(prediction.get("id")), {}).get("calibrated_probability"),
                        safe_float(prediction.get("probability_up"), 0.5),
                    ),
                }
                for prediction in predictions
            ]
            buy_probability = _fallback_buy_probability(enriched_predictions, performances)

        if meta_model.regressor is not None and len(features):
            expected_return = safe_float(meta_model.regressor.predict(features)[0])
        else:
            expected_return = _fallback_expected_return(predictions, performances)

        risk_score = _risk_score(buy_probability, indicator, regime)
        rows.append(
            {
                "stock_id": stock_id,
                "timestamp": timestamp,
                "buy_probability": buy_probability,
                "sell_probability": clamp(1.0 - buy_probability),
                "expected_return": expected_return,
                "risk_score": risk_score,
                "suggested_hold_days": _suggested_hold_days(risk_score, regime),
                "signal_type": _signal_type(buy_probability, expected_return),
            }
        )

    stored = repository.upsert_ensemble_signals(rows)
    return {"signals": len(stored), "meta_model_training_samples": meta_model.sample_size}
