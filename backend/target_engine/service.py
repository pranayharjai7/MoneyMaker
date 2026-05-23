from __future__ import annotations

from typing import Any
from backend.core.math_utils import clamp, safe_float

def calculate_profit_targets(
    suggested_entry_price: float,
    atr_proxy: float,
    indicators: dict[str, Any],
    regime: str,
    buy_probability: float,
) -> list[dict[str, Any]]:
    """Generate probabilistic take-profit targets (TP1, TP2, TP3).
    
    Returns:
        list[dict]: List of targets, each with 'label' (TP1, TP2, TP3), 'price', and 'probability'.
    """
    # 1. Adjust ATR multiplier spacing based on market regime
    if regime == "BULL TREND":
        spacing_multiplier = 1.3  # Extend targets in bull trends
        probability_multiplier = 1.05
    elif regime == "BEAR TREND":
        spacing_multiplier = 0.75  # Tighten targets in bear trends
        probability_multiplier = 0.85
    elif regime == "HIGH VOLATILITY":
        spacing_multiplier = 1.1   # Volatile range implies larger potential swings
        probability_multiplier = 0.90
    else:
        spacing_multiplier = 1.0   # Sideways / default standard spacing
        probability_multiplier = 0.95

    # Base steps in units of ATR
    step1 = 1.2 * spacing_multiplier
    step2 = 2.4 * spacing_multiplier
    step3 = 3.6 * spacing_multiplier

    tp1_price = suggested_entry_price + (step1 * atr_proxy)
    tp2_price = suggested_entry_price + (step2 * atr_proxy)
    tp3_price = suggested_entry_price + (step3 * atr_proxy)

    # 2. Map probabilities for each target
    # Probability decreases for further targets based on cumulative normal distribution shape
    tp1_prob = buy_probability * 0.92 * probability_multiplier
    tp2_prob = buy_probability * 0.68 * probability_multiplier
    tp3_prob = buy_probability * 0.42 * probability_multiplier

    # Ensure probabilities are within bounded logical ranges
    tp1_prob = clamp(tp1_prob, 0.05, 0.95)
    tp2_prob = clamp(tp2_prob, 0.03, 0.85)
    tp3_prob = clamp(tp3_prob, 0.01, 0.70)

    return [
        {
            "target_label": "TP1",
            "target_price": round(tp1_price, 2),
            "probability": round(tp1_prob, 3),
        },
        {
            "target_label": "TP2",
            "target_price": round(tp2_price, 2),
            "probability": round(tp2_prob, 3),
        },
        {
            "target_label": "TP3",
            "target_price": round(tp3_price, 2),
            "probability": round(tp3_prob, 3),
        },
    ]
