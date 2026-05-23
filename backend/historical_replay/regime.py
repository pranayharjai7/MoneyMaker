from __future__ import annotations

from datetime import UTC, datetime
from statistics import fmean
from typing import Any

import numpy as np
import pandas as pd

from backend.core.math_utils import clamp, safe_float
from backend.regime.service import REGIME_LABELS, _classify, _liquidity_score, _moving_average


def _closes(prices: pd.DataFrame) -> np.ndarray:
    if prices.empty:
        return np.array([])
    return np.array([safe_float(value) for value in prices["close"].tolist() if safe_float(value) > 0])


def _returns(closes: np.ndarray) -> np.ndarray:
    if len(closes) < 2:
        return np.array([])
    return np.diff(closes) / closes[:-1]


def detect_regime_at(
    benchmark_prices: pd.DataFrame,
    *,
    sector_correlation_shift: float = 0.0,
) -> dict[str, Any]:
    """Point-in-time regime using only benchmark bars before the replay day."""
    closes = _closes(benchmark_prices)
    if len(closes) < 30:
        return {
            "current_regime": REGIME_LABELS["sideways"],
            "confidence": 0.35,
            "volatility_proxy": 0.0,
            "sector_correlation_shift": sector_correlation_shift,
        }

    latest_close = safe_float(closes[-1])
    sma_20 = _moving_average(closes, 20)
    sma_50 = _moving_average(closes, 50)
    returns = _returns(closes)
    spx_trend = (latest_close / sma_50) - 1.0 if sma_50 > 0 else 0.0
    moving_average_spread = (sma_20 / sma_50) - 1.0 if sma_50 > 0 else 0.0
    volatility_proxy = safe_float(np.std(returns[-20:]) * np.sqrt(252.0)) if len(returns) else 0.0
    liquidity_score = _liquidity_score(
        [{"volume": safe_float(value)} for value in benchmark_prices["volume"].tolist()]
    )
    current_regime, confidence = _classify(
        spx_trend=spx_trend,
        volatility_proxy=volatility_proxy,
        moving_average_spread=moving_average_spread,
        sector_correlation_shift=sector_correlation_shift,
        liquidity_score=liquidity_score,
    )
    return {
        "current_regime": current_regime,
        "confidence": confidence,
        "volatility_proxy": volatility_proxy,
        "sector_correlation_shift": sector_correlation_shift,
    }


def _iso_timestamp(prices: pd.DataFrame) -> str:
    if prices.empty:
        return datetime.now(tz=UTC).isoformat()
    return pd.to_datetime(prices.iloc[-1]["timestamp"], utc=True).isoformat()
