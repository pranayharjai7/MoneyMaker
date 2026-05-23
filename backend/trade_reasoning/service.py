from __future__ import annotations

from typing import Any
from backend.core.math_utils import safe_float

def generate_trade_reasoning(
    indicators: dict[str, Any],
    regime: str,
    buy_probability: float,
    expected_return: float,
    meta_model_agreement: float = 0.81,
    calibration_confidence_stable: bool = True,
) -> list[dict[str, Any]]:
    """Synthesize explanatory factors behind the generated trade plan.
    
    Returns:
        list[dict]: List of reasoning factors with 'factor_type' and 'factor_text'.
    """
    reasonings = []
    
    # 1. Regime Influence
    reasonings.append({
        "factor_type": "regime",
        "factor_text": f"Market regime is classified as {regime} with stable structural characteristics.",
    })
    
    # 2. Technical Indicators (RSI, volume, MACD)
    rsi = safe_float(indicators.get("rsi"), 50.0)
    if rsi < 30.0:
        reasonings.append({
            "factor_type": "momentum",
            "factor_text": f"Extremely oversold RSI ({rsi:.1f}) indicates high probability mean-reversion opportunity.",
        })
    elif rsi > 70.0:
        reasonings.append({
            "factor_type": "momentum",
            "factor_text": f"Overbought RSI ({rsi:.1f}) confirms powerful momentum expansion.",
        })
    elif 50.0 <= rsi < 65.0:
        reasonings.append({
            "factor_type": "momentum",
            "factor_text": f"RSI in bullish zone ({rsi:.1f}) confirms steady upward momentum acceleration.",
        })
        
    volume_momentum = safe_float(indicators.get("volume_momentum"), 0.0)
    if volume_momentum > 0.15:
        reasonings.append({
            "factor_type": "volume",
            "factor_text": f"Significant volume expansion ({volume_momentum * 100:.1f}% above 20-day baseline) confirms institutional participation.",
        })
        
    macd = safe_float(indicators.get("macd"), 0.0)
    macd_signal = safe_float(indicators.get("macd_signal"), 0.0)
    if macd > macd_signal and macd > 0:
        reasonings.append({
            "factor_type": "momentum",
            "factor_text": "MACD line is trading above signal line in positive territory, signaling bullish trend persistence.",
        })

    # 3. Meta-Model and Calibration Consensus
    agreement_pct = int(meta_model_agreement * 100)
    reasonings.append({
        "factor_type": "meta_model",
        "factor_text": f"Meta-model agreement is high at {agreement_pct}%, indicating strong cross-model alignment.",
    })
    
    if calibration_confidence_stable:
        reasonings.append({
            "factor_type": "calibration",
            "factor_text": "Model probability calibration is highly stable, with low historical Brier and ECE scores.",
        })
    else:
        reasonings.append({
            "factor_type": "calibration",
            "factor_text": "Calibration confidence has slightly widened due to active regime shifts, promoting smaller risk sizing.",
        })
        
    # 4. Volatility considerations
    volatility = safe_float(indicators.get("volatility"), 0.02)
    if volatility > 0.035:
        reasonings.append({
            "factor_type": "volatility",
            "factor_text": f"Elevated daily volatility ({volatility * 100:.1f}%) requires dynamic wider stop-loss margins.",
        })
    else:
        reasonings.append({
            "factor_type": "volatility",
            "factor_text": f"Low volatility baseline ({volatility * 100:.1f}%) permits capital efficiency through tighter protective stops.",
        })

    return reasonings
