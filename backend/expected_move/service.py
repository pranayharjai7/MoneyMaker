from __future__ import annotations

import math
from typing import Any
from backend.core.math_utils import clamp, safe_float

def calculate_expected_move(
    current_price: float,
    indicators: dict[str, Any],
    regime: str,
    buy_probability: float,
    horizon_days: int = 5,
) -> dict[str, Any]:
    """Estimate a realistic future movement range over a specified holding window.
    
    Returns:
        dict: Containing 'expected_upside_pct', 'expected_downside_pct',
              'confidence_interval_low', 'confidence_interval_high'.
    """
    volatility = safe_float(indicators.get("volatility"), 0.02)  # Daily historical volatility as percentage
    
    # 1. Base standard expected move over horizon: Vol = DailyVol * sqrt(Horizon)
    standard_move_pct = volatility * math.sqrt(horizon_days)
    
    # 2. Adjust asymmetry based on market regime and buy_probability
    # Under pure symmetry, a 1-sigma move is StandardMove.
    # We tilt this distribution using current market context.
    upside_tilt = 1.0
    downside_tilt = 1.0

    if regime == "BULL TREND":
        upside_tilt += 0.25
        downside_tilt -= 0.15
    elif regime == "BEAR TREND":
        upside_tilt -= 0.20
        downside_tilt += 0.30
    elif regime == "HIGH VOLATILITY":
        upside_tilt += 0.15
        downside_tilt += 0.25
    
    # In addition, tilt based on the buy/sell signal strength
    probability_tilt = (buy_probability - 0.5) * 2.0  # Range: -1.0 to 1.0
    if probability_tilt > 0:
        upside_tilt += 0.15 * probability_tilt
        downside_tilt -= 0.10 * probability_tilt
    else:
        upside_tilt -= 0.10 * abs(probability_tilt)
        downside_tilt += 0.15 * abs(probability_tilt)

    expected_upside_pct = standard_move_pct * upside_tilt
    expected_downside_pct = standard_move_pct * downside_tilt

    # Ensure bounds are strictly positive
    expected_upside_pct = clamp(expected_upside_pct, 0.005, 0.25)
    expected_downside_pct = clamp(expected_downside_pct, 0.005, 0.25)

    # 3. Formulate confidence intervals
    # CI = CurrentPrice * (1 +/- Move)
    ci_high = current_price * (1.0 + expected_upside_pct)
    ci_low = current_price * (1.0 - expected_downside_pct)

    return {
        "expected_upside_pct": round(expected_upside_pct * 100, 2),  # Output in percent unit e.g. 4.2
        "expected_downside_pct": round(expected_downside_pct * 100, 2), # Output in percent unit e.g. 2.1
        "confidence_interval_low": round(ci_low, 2),
        "confidence_interval_high": round(ci_high, 2),
    }
