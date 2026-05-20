from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from backend.core.math_utils import clamp, safe_float
from backend.db.repository import SupabaseRepository


@dataclass(frozen=True)
class EnsembleSignal:
    stock_id: str
    timestamp: str
    buy_probability: float
    sell_probability: float
    expected_return: float
    risk_score: float
    suggested_hold_days: int
    signal_type: str

    def to_row(self) -> dict[str, object]:
        return {
            "stock_id": self.stock_id,
            "timestamp": self.timestamp,
            "buy_probability": clamp(self.buy_probability),
            "sell_probability": clamp(self.sell_probability),
            "expected_return": safe_float(self.expected_return),
            "risk_score": clamp(self.risk_score),
            "suggested_hold_days": max(1, self.suggested_hold_days),
            "signal_type": self.signal_type,
        }


def _weighted_average(values: list[tuple[float, float]]) -> float:
    total_weight = sum(weight for _, weight in values)
    if total_weight == 0:
        return 0.0
    return sum(value * weight for value, weight in values) / total_weight


def combine_model_outputs(
    stock_id: str,
    timestamp: str,
    predictions: Iterable[Mapping[str, Any]],
    latest_indicator: Mapping[str, Any] | None = None,
    weights: Mapping[str, float] | None = None,
) -> EnsembleSignal:
    weighted_probabilities: list[tuple[float, float]] = []
    weighted_returns: list[tuple[float, float]] = []
    weighted_confidences: list[tuple[float, float]] = []

    for prediction in predictions:
        model_name = str(prediction.get("model_name"))
        confidence = clamp(safe_float(prediction.get("confidence"), 0.0))
        expected_return = safe_float(prediction.get("expected_return"))
        probability = clamp(safe_float(prediction.get("probability_up"), 0.5))
        weight = (
            weights.get(model_name, 0.0)
            if weights is not None
            else confidence * (0.25 + abs(probability - 0.5) * 2.0 + abs(expected_return))
        )
        if weight <= 0:
            continue
        effective_weight = weight * max(confidence, 0.05)
        weighted_probabilities.append((probability, effective_weight))
        weighted_returns.append((expected_return, effective_weight))
        weighted_confidences.append((confidence, weight))

    buy_probability = clamp(_weighted_average(weighted_probabilities) if weighted_probabilities else 0.5)
    sell_probability = clamp(1.0 - buy_probability)
    expected_return = _weighted_average(weighted_returns) if weighted_returns else 0.0
    confidence = clamp(_weighted_average(weighted_confidences) if weighted_confidences else 0.0)
    volatility = safe_float((latest_indicator or {}).get("volatility"), 0.02)
    risk_score = clamp(((1.0 - confidence) * 0.65) + min(volatility * 5.0, 1.0) * 0.35)

    if buy_probability >= 0.65 and expected_return > 0:
        signal_type = "buy"
    elif sell_probability >= 0.65 and expected_return < 0:
        signal_type = "sell"
    else:
        signal_type = "neutral"

    if risk_score < 0.35:
        suggested_hold_days = 10
    elif risk_score < 0.55:
        suggested_hold_days = 5
    else:
        suggested_hold_days = 2

    return EnsembleSignal(
        stock_id=stock_id,
        timestamp=timestamp,
        buy_probability=buy_probability,
        sell_probability=sell_probability,
        expected_return=expected_return,
        risk_score=risk_score,
        suggested_hold_days=suggested_hold_days,
        signal_type=signal_type,
    )


def generate_ensemble_signals(
    repository: SupabaseRepository | None = None,
    stock_ids: Iterable[str] | None = None,
    weights: Mapping[str, float] | None = None,
) -> dict[str, int]:
    if weights is None:
        from backend.meta_model.service import generate_meta_model_signals

        return generate_meta_model_signals(repository=repository, stock_ids=stock_ids)

    repository = repository or SupabaseRepository()
    if stock_ids is None:
        stock_ids = [stock["id"] for stock in repository.list_stocks()]

    rows: list[dict[str, object]] = []
    for stock_id in stock_ids:
        predictions = repository.get_model_predictions(stock_id, limit=50)
        if not predictions:
            continue
        latest_timestamp = max(str(prediction["timestamp"]) for prediction in predictions)
        latest_predictions = [
            prediction for prediction in predictions if str(prediction["timestamp"]) == latest_timestamp
        ]
        indicators = repository.get_indicators(stock_id, limit=1)
        latest_indicator = indicators[-1] if indicators else {}
        signal = combine_model_outputs(
            stock_id=stock_id,
            timestamp=latest_timestamp,
            predictions=latest_predictions,
            latest_indicator=latest_indicator,
            weights=weights,
        )
        rows.append(signal.to_row())

    stored = repository.upsert_ensemble_signals(rows)
    return {"signals": len(stored)}
