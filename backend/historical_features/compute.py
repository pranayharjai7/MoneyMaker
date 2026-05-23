from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from backend.features.indicators import INDICATOR_COLUMNS, compute_technical_indicators

HISTORICAL_FEATURE_COLUMNS = [
    *INDICATOR_COLUMNS,
    "atr",
    "rolling_beta_spy",
    "sector_relative_strength",
    "volatility_percentile",
    "trend_persistence",
]

SECTOR_ETF_BY_SECTOR: dict[str, str] = {
    "TECHNOLOGY": "XLK",
    "FINANCIALS": "XLF",
    "FINANCIAL SERVICES": "XLF",
    "ENERGY": "XLE",
    "HEALTHCARE": "XLV",
    "HEALTH CARE": "XLV",
    "INDUSTRIALS": "XLI",
    "CONSUMER DISCRETIONARY": "XLY",
    "CONSUMER STAPLES": "XLP",
    "UTILITIES": "XLU",
    "MATERIALS": "XLB",
    "REAL ESTATE": "XLRE",
    "COMMUNICATION SERVICES": "XLC",
    "COMMUNICATIONS": "XLC",
}


def _price_frame(price_rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not price_rows:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    frame = pd.DataFrame(price_rows)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    for column in ["open", "high", "low", "close", "volume"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.sort_values("timestamp").reset_index(drop=True)


def _returns(close: pd.Series) -> pd.Series:
    return close.pct_change()


def _rolling_beta(stock_returns: pd.Series, benchmark_returns: pd.Series, window: int = 60) -> pd.Series:
    covariance = stock_returns.rolling(window, min_periods=window).cov(benchmark_returns)
    variance = benchmark_returns.rolling(window, min_periods=window).var()
    return covariance / variance.replace(0, np.nan)


def _atr_series(prices: pd.DataFrame, window: int = 14) -> pd.Series:
    high_low = prices["high"] - prices["low"]
    high_close = (prices["high"] - prices["close"].shift()).abs()
    low_close = (prices["low"] - prices["close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.rolling(window=window, min_periods=window).mean()


def _volatility_percentile(returns: pd.Series, vol_window: int = 20, rank_window: int = 252) -> pd.Series:
    realized_vol = returns.rolling(vol_window, min_periods=vol_window).std()
    return realized_vol.rolling(rank_window, min_periods=vol_window).apply(
        lambda window: float(pd.Series(window).rank(pct=True).iloc[-1]) if len(window) else np.nan,
        raw=False,
    )


def _trend_persistence(returns: pd.Series, window: int = 10) -> pd.Series:
    def persistence(values: np.ndarray) -> float:
        if len(values) < 2:
            return np.nan
        signs = np.sign(values)
        if np.all(signs == 0):
            return 0.0
        same_direction = np.sum(signs[1:] == signs[:-1])
        return float(same_direction / (len(signs) - 1))

    return returns.rolling(window, min_periods=window).apply(persistence, raw=True)


def compute_historical_features(
    price_rows: list[dict[str, Any]],
    *,
    benchmark_rows: list[dict[str, Any]] | None = None,
    sector_rows: list[dict[str, Any]] | None = None,
) -> pd.DataFrame:
    """Compute features using only data available at each timestamp (backward-looking windows)."""
    prices = _price_frame(price_rows)
    if prices.empty:
        return pd.DataFrame(columns=["timestamp", *HISTORICAL_FEATURE_COLUMNS])

    base = compute_technical_indicators(prices)
    close = prices["close"]
    returns = _returns(close)
    atr = _atr_series(prices)

    benchmark = _price_frame(benchmark_rows or [])
    sector = _price_frame(sector_rows or [])

    rolling_beta_spy = pd.Series(index=prices.index, dtype=float)
    if not benchmark.empty:
        benchmark_close = (
            benchmark.set_index("timestamp")["close"]
            .reindex(prices["timestamp"])
            .ffill()
            .reset_index(drop=True)
        )
        benchmark_returns = _returns(benchmark_close)
        rolling_beta_spy = _rolling_beta(returns, benchmark_returns)

    sector_relative_strength = pd.Series(index=prices.index, dtype=float)
    if not sector.empty:
        sector_close = (
            sector.set_index("timestamp")["close"]
            .reindex(prices["timestamp"])
            .ffill()
            .reset_index(drop=True)
        )
        stock_momentum = close / close.shift(20) - 1
        sector_momentum = sector_close / sector_close.shift(20) - 1
        sector_relative_strength = stock_momentum - sector_momentum

    volatility_percentile = _volatility_percentile(returns)
    trend_persistence = _trend_persistence(returns)

    features = base.copy()
    features["atr"] = atr
    features["rolling_beta_spy"] = rolling_beta_spy
    features["sector_relative_strength"] = sector_relative_strength
    features["volatility_percentile"] = volatility_percentile
    features["trend_persistence"] = trend_persistence
    return features.replace({np.nan: None})


def sector_etf_for_stock(stock: dict[str, Any] | None) -> str:
    if not stock:
        return "SPY"
    sector = str(stock.get("sector") or "").strip().upper()
    return SECTOR_ETF_BY_SECTOR.get(sector, "SPY")
