from __future__ import annotations

from typing import Any
from backend.core.math_utils import clamp, safe_float

def calculate_hold_duration(
    base_suggested_hold_days: int,
    indicators: dict[str, Any],
    regime: str,
) -> dict[str, Any]:
    """Estimate optimal hold duration window in trading days.
    
    Returns:
        dict: Containing 'expected_hold_min_days' and 'expected_hold_max_days'.
    """
    volatility = safe_float(indicators.get("volatility"), 0.02)
    
    # 1. Base hold days calculation
    # Standard fallback holds between 3 to 10 days
    hold_base = float(base_suggested_hold_days)
    if hold_base <= 0:
        hold_base = 5.0
        
    # 2. Adjust hold time based on volatility
    # High volatility suggests faster decay and shorter holding periods to capture gains
    if volatility > 0.035:
        hold_base *= 0.70  # Shorten hold times by 30%
    elif volatility < 0.015:
        hold_base *= 1.20  # Stable low volatility allows longer trends to develop
        
    # 3. Adjust based on market regime
    if regime == "BULL TREND":
        hold_base *= 1.15  # Let profits run in bull regimes
    elif regime == "BEAR TREND":
        hold_base *= 0.65  # Be highly defensive and take fast profits/cut losses in bear regimes
    elif regime == "SIDEWAYS":
        hold_base *= 0.80  # Sideways markets have less trend persistence
    elif regime == "HIGH VOLATILITY":
        hold_base *= 0.70  # Exit quickly in highly volatile environments
        
    min_days = int(math_floor_or_ceil(hold_base * 0.8, is_min=True))
    max_days = int(math_floor_or_ceil(hold_base * 1.3, is_min=False))
    
    # Clean bounding
    min_days = int(clamp(min_days, 1, 15))
    max_days = int(clamp(max_days, min_days + 1, 20))
    
    return {
        "expected_hold_min_days": min_days,
        "expected_hold_max_days": max_days,
    }

def math_floor_or_ceil(value: float, is_min: bool) -> float:
    # Inline utility
    import math
    return math.floor(value) if is_min else math.ceil(value)
