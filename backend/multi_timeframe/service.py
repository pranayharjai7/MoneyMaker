from __future__ import annotations

from typing import Any, Mapping
import numpy as np
from backend.core.math_utils import safe_float

def calculate_timeframe_biases(
    prices: list[Mapping[str, Any]],
    indicators: dict[str, Any],
) -> dict[str, Any]:
    """Analyze weekly trend, daily trend, and short-term momentum to calculate biases.
    
    Returns:
        dict: Containing 'weekly_bias', 'daily_bias', 'intraday_bias', and a safety flag.
    """
    closes = np.array([safe_float(row.get("close")) for row in prices if safe_float(row.get("close")) > 0])
    
    # 1. Weekly Trend Bias (Weekly SMA 10 vs 30 proxy)
    # We construct weekly close estimates by taking every 5th close from the daily series
    if len(closes) >= 150:
        weekly_closes = closes[::-5][:30][::-1]  # Take up to 30 weekly closes
        w_sma_10 = np.mean(weekly_closes[-10:])
        w_sma_30 = np.mean(weekly_closes)
        latest_weekly = weekly_closes[-1]
        
        if latest_weekly > w_sma_10 > w_sma_30:
            weekly_bias = "Bullish"
        elif latest_weekly < w_sma_10 < w_sma_30:
            weekly_bias = "Bearish"
        else:
            weekly_bias = "Neutral"
    else:
        # Fallback to simple SMA spread
        sma_20 = safe_float(indicators.get("sma_20"), closes[-1] if len(closes) else 0)
        sma_50 = safe_float(indicators.get("sma_50"), closes[-1] if len(closes) else 0)
        if sma_20 > sma_50:
            weekly_bias = "Bullish"
        elif sma_20 < sma_50:
            weekly_bias = "Bearish"
        else:
            weekly_bias = "Neutral"

    # 2. Daily Trend Bias (Daily close vs SMA 20 / SMA 50)
    latest_close = closes[-1] if len(closes) else 0
    sma_20 = safe_float(indicators.get("sma_20"), latest_close)
    sma_50 = safe_float(indicators.get("sma_50"), latest_close)
    
    if latest_close > sma_20 and latest_close > sma_50:
        daily_bias = "Bullish"
    elif latest_close < sma_20 and latest_close < sma_50:
        daily_bias = "Bearish"
    else:
        daily_bias = "Neutral"

    # 3. Intraday / Short-Term Momentum Bias (RSI & MACD)
    rsi = safe_float(indicators.get("rsi"), 50.0)
    macd = safe_float(indicators.get("macd"), 0.0)
    macd_signal = safe_float(indicators.get("macd_signal"), 0.0)
    
    if rsi >= 55.0 and macd > macd_signal:
        intraday_bias = "Bullish"
    elif rsi <= 45.0 and macd < macd_signal:
        intraday_bias = "Bearish"
    else:
        intraday_bias = "Neutral"

    # 4. Multi-Timeframe Trend Incongruency Guardrail
    # Prevent going long when the macro weekly trend is bearish
    counter_trend_warning = False
    if weekly_bias == "Bearish" and (daily_bias == "Bullish" or intraday_bias == "Bullish"):
        counter_trend_warning = True

    return {
        "weekly_bias": weekly_bias,
        "daily_bias": daily_bias,
        "intraday_bias": intraday_bias,
        "counter_trend_warning": counter_trend_warning,
    }
