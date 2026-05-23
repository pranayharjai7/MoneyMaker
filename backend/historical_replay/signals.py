from __future__ import annotations

from typing import Any

import pandas as pd

from backend.ensemble.service import combine_model_outputs
from backend.meta_model.service import (
    _fallback_buy_probability,
    _fallback_expected_return,
    _risk_score,
    _signal_type,
    _suggested_hold_days,
)
from backend.models.registry import get_default_models


def _indicator_row(features: pd.DataFrame) -> dict[str, Any] | None:
    if features.empty:
        return None
    return features.iloc[-1].to_dict()


def generate_point_in_time_signal(
    *,
    stock_id: str,
    prices: pd.DataFrame,
    features: pd.DataFrame,
    regime: dict[str, Any],
    signal_timestamp: str,
    meta_model_version: str = "replay_v1",
    model_performances: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Run trading models on sliced history and emit one historical signal row."""
    if prices.empty or features.empty:
        return None

    model_rows: list[dict[str, Any]] = []
    for model in get_default_models():
        prediction = model.predict(stock_id, prices, features)
        if not prediction.timestamp:
            continue
        model_rows.append(prediction.to_row())

    if not model_rows:
        return None

    indicator = _indicator_row(features)
    performances = model_performances or {}
    buy_probability = _fallback_buy_probability(model_rows, performances)
    expected_return = _fallback_expected_return(model_rows, performances)
    risk_score = _risk_score(buy_probability, indicator, regime)
    signal_type = _signal_type(buy_probability, expected_return)
    hold_days = _suggested_hold_days(risk_score, regime)

    ensemble = combine_model_outputs(
        stock_id,
        signal_timestamp,
        model_rows,
        latest_indicator=indicator,
    )

    return {
        "stock_id": stock_id,
        "timestamp": signal_timestamp,
        "signal_type": signal_type,
        "probability": buy_probability if signal_type != "sell" else 1.0 - buy_probability,
        "expected_return": expected_return,
        "risk_score": risk_score,
        "hold_days": hold_days,
        "regime": str(regime.get("current_regime") or "SIDEWAYS"),
        "meta_model_version": meta_model_version,
        "model_predictions": model_rows,
        "ensemble_buy_probability": ensemble.buy_probability,
        "ensemble_expected_return": ensemble.expected_return,
    }
