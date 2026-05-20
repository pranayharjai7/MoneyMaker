from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from statistics import fmean
from typing import Any

import numpy as np

from backend.core.math_utils import clamp, safe_float
from backend.db.repository import SupabaseRepository


REFERENCE_INDEX_TICKERS = ("SPX", "^GSPC", "SPY")
REGIME_LABELS = {
    "bull": "BULL TREND",
    "bear": "BEAR TREND",
    "sideways": "SIDEWAYS",
    "high_volatility": "HIGH VOLATILITY",
    "low_liquidity": "LOW LIQUIDITY",
}


def _to_utc_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value)
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _closes(prices: list[Mapping[str, Any]]) -> np.ndarray:
    return np.array([safe_float(row.get("close")) for row in prices if safe_float(row.get("close")) > 0])


def _volumes(prices: list[Mapping[str, Any]]) -> np.ndarray:
    return np.array([safe_float(row.get("volume")) for row in prices if safe_float(row.get("volume")) > 0])


def _returns(closes: np.ndarray) -> np.ndarray:
    if len(closes) < 2:
        return np.array([])
    return np.diff(closes) / closes[:-1]


def _reference_prices(repository: SupabaseRepository, limit: int = 252) -> tuple[str | None, list[dict[str, Any]]]:
    for ticker in REFERENCE_INDEX_TICKERS:
        prices = repository.get_prices_for_ticker(ticker, limit=limit)
        if len(prices) >= 30:
            return ticker, prices
    return None, []


def _moving_average(values: np.ndarray, window: int) -> float:
    if len(values) < window:
        return safe_float(np.mean(values)) if len(values) else 0.0
    return safe_float(np.mean(values[-window:]))


def _liquidity_score(reference_prices: list[Mapping[str, Any]]) -> float:
    volumes = _volumes(reference_prices)
    if len(volumes) < 40:
        return 1.0
    recent = safe_float(np.mean(volumes[-10:]))
    baseline = safe_float(np.mean(volumes[-60:-10]))
    if baseline <= 0:
        return 1.0
    return clamp(recent / baseline)


def _pairwise_mean_correlation(series: list[np.ndarray]) -> float:
    correlations = []
    for left_index, left in enumerate(series):
        for right in series[left_index + 1 :]:
            length = min(len(left), len(right))
            if length < 8:
                continue
            corr = np.corrcoef(left[-length:], right[-length:])[0, 1]
            if not np.isnan(corr):
                correlations.append(float(corr))
    return fmean(correlations) if correlations else 0.0


def _sector_correlation_shift(repository: SupabaseRepository, limit: int = 120) -> float:
    return_series = []
    for stock in repository.list_stocks()[:40]:
        ticker = stock.get("ticker")
        if not ticker or str(ticker).upper() in REFERENCE_INDEX_TICKERS:
            continue
        prices = repository.get_prices(str(stock["id"]), limit=limit)
        returns = _returns(_closes(prices))
        if len(returns) >= 50:
            return_series.append(returns)

    if len(return_series) < 2:
        return 0.0
    recent = [series[-20:] for series in return_series]
    previous = [series[-40:-20] for series in return_series if len(series) >= 40]
    return safe_float(_pairwise_mean_correlation(recent) - _pairwise_mean_correlation(previous))


def _classify(
    spx_trend: float,
    volatility_proxy: float,
    moving_average_spread: float,
    sector_correlation_shift: float,
    liquidity_score: float,
) -> tuple[str, float]:
    if liquidity_score < 0.45:
        confidence = clamp(0.55 + (0.45 - liquidity_score) * 1.2)
        return REGIME_LABELS["low_liquidity"], confidence

    if volatility_proxy > 0.35 or (volatility_proxy > 0.28 and sector_correlation_shift > 0.15):
        confidence = clamp(0.55 + (volatility_proxy - 0.25) * 1.4 + max(sector_correlation_shift, 0) * 0.4)
        return REGIME_LABELS["high_volatility"], confidence

    if spx_trend > 0.03 and moving_average_spread > 0:
        confidence = clamp(0.52 + abs(spx_trend) * 5.0 + abs(moving_average_spread) * 3.0)
        return REGIME_LABELS["bull"], confidence

    if spx_trend < -0.03 and moving_average_spread < 0:
        confidence = clamp(0.52 + abs(spx_trend) * 5.0 + abs(moving_average_spread) * 3.0)
        return REGIME_LABELS["bear"], confidence

    confidence = clamp(0.72 - abs(spx_trend) * 3.0 - abs(moving_average_spread) * 2.0)
    return REGIME_LABELS["sideways"], confidence


def detect_market_regime(repository: SupabaseRepository | None = None) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    reference_ticker, prices = _reference_prices(repository)
    closes = _closes(prices)
    if len(closes) < 30:
        timestamp = datetime.now(tz=UTC)
        return {
            "timestamp": _iso(timestamp),
            "current_regime": REGIME_LABELS["sideways"],
            "confidence": 0.35,
            "spx_trend": 0.0,
            "volatility_proxy": 0.0,
            "moving_average_spread": 0.0,
            "sector_correlation_shift": 0.0,
            "liquidity_score": 1.0,
            "feature_payload": {"reference_ticker": reference_ticker, "reason": "insufficient_history"},
        }

    latest_close = safe_float(closes[-1])
    sma_20 = _moving_average(closes, 20)
    sma_50 = _moving_average(closes, 50)
    returns = _returns(closes)
    spx_trend = (latest_close / sma_50) - 1.0 if sma_50 > 0 else 0.0
    moving_average_spread = (sma_20 / sma_50) - 1.0 if sma_50 > 0 else 0.0
    volatility_proxy = safe_float(np.std(returns[-20:]) * np.sqrt(252.0)) if len(returns) else 0.0
    liquidity_score = _liquidity_score(prices)
    sector_correlation_shift = _sector_correlation_shift(repository)
    current_regime, confidence = _classify(
        spx_trend=spx_trend,
        volatility_proxy=volatility_proxy,
        moving_average_spread=moving_average_spread,
        sector_correlation_shift=sector_correlation_shift,
        liquidity_score=liquidity_score,
    )
    timestamp = _to_utc_datetime(prices[-1]["timestamp"])

    return {
        "timestamp": _iso(timestamp),
        "current_regime": current_regime,
        "confidence": confidence,
        "spx_trend": spx_trend,
        "volatility_proxy": volatility_proxy,
        "moving_average_spread": moving_average_spread,
        "sector_correlation_shift": sector_correlation_shift,
        "liquidity_score": liquidity_score,
        "feature_payload": {
            "reference_ticker": reference_ticker,
            "sma_20": sma_20,
            "sma_50": sma_50,
            "latest_close": latest_close,
        },
    }


def refresh_market_regime(repository: SupabaseRepository | None = None) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    regime = detect_market_regime(repository=repository)
    stored = repository.upsert_market_regime(regime)
    return stored or regime
