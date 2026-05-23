from __future__ import annotations

from typing import Any
from backend.core.math_utils import clamp, safe_float

def calculate_entry_zones(
    current_price: float,
    indicators: dict[str, Any],
    regime: str,
) -> dict[str, Any]:
    """Determine optimal entry zones and suggested entries.
    
    Returns:
        dict: Containing 'buy_zone_low', 'buy_zone_high', 'suggested_entry_price',
              'entry_type', 'entry_timing', 'entry_score'.
    """
    rsi = safe_float(indicators.get("rsi"), 50.0)
    sma_20 = safe_float(indicators.get("sma_20"), current_price)
    sma_50 = safe_float(indicators.get("sma_50"), current_price)
    bollinger_upper = safe_float(indicators.get("bollinger_upper"), current_price * 1.05)
    bollinger_lower = safe_float(indicators.get("bollinger_lower"), current_price * 0.95)
    volume_momentum = safe_float(indicators.get("volume_momentum"), 0.0)
    macd = safe_float(indicators.get("macd"), 0.0)
    macd_signal = safe_float(indicators.get("macd_signal"), 0.0)
    
    # 1. Identify optimal Entry Type based on indicators and regime
    if regime == "SIDEWAYS" and (rsi < 35 or current_price <= bollinger_lower * 1.02):
        entry_type = "Mean Reversion"
        entry_timing = "Wait for pullback to key dynamic support near Bollinger Lower Band"
        buy_zone_low = bollinger_lower * 0.99
        buy_zone_high = bollinger_lower * 1.02
        suggested_entry_price = bollinger_lower * 1.01
    elif current_price >= bollinger_upper * 0.98 and volume_momentum > 0.15:
        entry_type = "Breakout"
        entry_timing = f"Breakout above {bollinger_upper:.2f} confirms strong momentum"
        buy_zone_low = bollinger_upper * 0.995
        buy_zone_high = bollinger_upper * 1.02
        suggested_entry_price = bollinger_upper * 1.005
    elif current_price > sma_50 and rsi < 48:
        entry_type = "Pullback"
        entry_timing = "Wait for intraday pullback to 20-day SMA or key horizontal support"
        buy_zone_low = min(sma_20, current_price * 0.98)
        buy_zone_high = max(sma_20 * 1.01, current_price * 0.99)
        suggested_entry_price = (buy_zone_low + buy_zone_high) / 2.0
    else:
        entry_type = "Momentum Continuation"
        entry_timing = "Enter now to capture persistent momentum acceleration"
        buy_zone_low = current_price * 0.99
        buy_zone_high = current_price * 1.01
        suggested_entry_price = current_price

    # Ensure clean price boundaries
    if buy_zone_low > buy_zone_high:
        buy_zone_low, buy_zone_high = buy_zone_high, buy_zone_low

    # 2. Score Entry (0 to 100)
    score = 50.0  # Base score
    
    # Trend persistence / Regime alignment
    if regime == "BULL TREND":
        score += 15.0
        if entry_type in ("Pullback", "Momentum Continuation"):
            score += 10.0
    elif regime == "BEAR TREND":
        score -= 20.0
        if entry_type != "Pullback":
            score -= 10.0
    elif regime == "HIGH VOLATILITY":
        score -= 10.0  # Reduce entry quality in highly volatile markets
        
    # Volatility / Indicators confirmations
    if 40.0 <= rsi <= 60.0:
        score += 5.0
    elif rsi > 70.0:
        score -= 5.0  # Slightly penalize overbought entries
    elif rsi < 30.0:
        score += 10.0 if entry_type == "Mean Reversion" else -5.0

    if volume_momentum > 0.1:
        score += 10.0
    if macd > macd_signal:
        score += 5.0

    entry_score = clamp(score, 10.0, 99.0)  # Keep in clean professional range

    return {
        "buy_zone_low": round(buy_zone_low, 2),
        "buy_zone_high": round(buy_zone_high, 2),
        "suggested_entry_price": round(suggested_entry_price, 2),
        "entry_type": entry_type,
        "entry_timing": entry_timing,
        "entry_score": round(entry_score, 1),
    }
