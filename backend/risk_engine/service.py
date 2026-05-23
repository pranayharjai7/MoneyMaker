from __future__ import annotations

from typing import Any
from backend.core.math_utils import clamp, safe_float

def calculate_risk_parameters(
    suggested_entry_price: float,
    indicators: dict[str, Any],
    regime: str,
    regime_confidence: float = 0.8,
) -> dict[str, Any]:
    """Calculate dynamic stop loss, trailing stop, and position risk parameters.
    
    Returns:
        dict: Containing 'stop_loss', 'max_suggested_risk_pct', 'trailing_stop_desc', 'risk_reward_ratio' placeholder.
              Note: risk_reward_ratio is calibrated relative to TP1 later in the planner.
    """
    volatility = safe_float(indicators.get("volatility"), 0.02)  # Daily historical volatility as percentage
    
    # Estimate average true range (ATR) proxy from daily volatility
    atr_proxy = suggested_entry_price * volatility
    if atr_proxy <= 0:
        atr_proxy = suggested_entry_price * 0.02

    # 1. Determine dynamic stop loss multiplier based on regime
    if regime == "HIGH VOLATILITY":
        multiplier = 2.5
    elif regime == "BEAR TREND":
        multiplier = 2.2
    elif regime == "BULL TREND":
        multiplier = 1.8  # Tighter stops allowed in stable bull trends
    else:
        multiplier = 2.0  # Sideways / range bound default

    stop_loss = suggested_entry_price - (multiplier * atr_proxy)
    
    # Keep stop loss realistic (minimum 1.5% below entry, max 8% below entry to preserve capital)
    min_stop = suggested_entry_price * 0.985
    max_stop = suggested_entry_price * 0.92
    if stop_loss > min_stop:
        stop_loss = min_stop
    elif stop_loss < max_stop:
        stop_loss = max_stop

    # 2. Position Sizing Suggestion (based on regime confidence and severity)
    base_risk = 2.0  # standard 2.0% risk rule
    if regime == "BULL TREND":
        max_suggested_risk_pct = base_risk + (0.5 * regime_confidence)
    elif regime == "BEAR TREND":
        max_suggested_risk_pct = base_risk - (1.0 * regime_confidence)
    elif regime == "HIGH VOLATILITY":
        max_suggested_risk_pct = base_risk - (0.8 * regime_confidence)
    else:
        max_suggested_risk_pct = base_risk - (0.2 * regime_confidence)

    max_suggested_risk_pct = clamp(max_suggested_risk_pct, 0.5, 3.0)

    # 3. Trailing Stop formulation
    trailing_multiplier = multiplier * 0.8
    trailing_stop_desc = f"Trail stop {trailing_multiplier:.1f}× ATR ({trailing_multiplier * (volatility * 100):.1f}%) below local high once trade is in profit"

    return {
        "stop_loss": round(stop_loss, 2),
        "max_suggested_risk_pct": round(max_suggested_risk_pct, 2),
        "trailing_stop_desc": trailing_stop_desc,
        "atr_proxy": atr_proxy,
    }
