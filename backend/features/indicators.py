from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd

from backend.db.repository import SupabaseRepository


INDICATOR_COLUMNS = [
    "rsi",
    "macd",
    "macd_signal",
    "sma_20",
    "sma_50",
    "bollinger_upper",
    "bollinger_lower",
    "volatility",
    "volume_momentum",
]


def _fallback_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window=window, min_periods=window).mean()
    loss = -delta.clip(upper=0).rolling(window=window, min_periods=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _fallback_atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.rolling(window=window, min_periods=window).mean()


def compute_technical_indicators(prices: pd.DataFrame) -> pd.DataFrame:
    """Compute RSI, MACD, moving averages, Bollinger bands, ATR, and volume momentum."""

    if prices.empty:
        return pd.DataFrame(columns=["timestamp", *INDICATOR_COLUMNS])

    df = prices.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)

    if len(df) < 5:  # Minimum for volume_momentum
        return pd.DataFrame({"timestamp": df["timestamp"]}).assign(
            **{col: None for col in INDICATOR_COLUMNS}
        )

    for column in ["open", "high", "low", "close", "volume"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]
    n = len(df)

    try:
        from ta.momentum import RSIIndicator
        from ta.trend import MACD, SMAIndicator
        from ta.volatility import AverageTrueRange, BollingerBands

        rsi = RSIIndicator(close=close, window=14).rsi() if n >= 14 else pd.Series(index=df.index, dtype=float)
        macd_indicator = MACD(close=close, window_slow=26, window_fast=12, window_sign=9) if n >= 26 else None
        macd = macd_indicator.macd() if macd_indicator else pd.Series(index=df.index, dtype=float)
        macd_signal = macd_indicator.macd_signal() if macd_indicator else pd.Series(index=df.index, dtype=float)
        sma_20 = SMAIndicator(close=close, window=20).sma_indicator() if n >= 20 else pd.Series(index=df.index, dtype=float)
        sma_50 = SMAIndicator(close=close, window=50).sma_indicator() if n >= 50 else pd.Series(index=df.index, dtype=float)
        bollinger = BollingerBands(close=close, window=20, window_dev=2) if n >= 20 else None
        bollinger_upper = bollinger.bollinger_hband() if bollinger else pd.Series(index=df.index, dtype=float)
        bollinger_lower = bollinger.bollinger_lband() if bollinger else pd.Series(index=df.index, dtype=float)
        atr = AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range() if n >= 14 else pd.Series(index=df.index, dtype=float)
    except (ImportError, Exception):
        rsi = _fallback_rsi(close) if n >= 14 else pd.Series(index=df.index, dtype=float)
        ema_fast = close.ewm(span=12, adjust=False).mean() if n >= 12 else None
        ema_slow = close.ewm(span=26, adjust=False).mean() if n >= 26 else None
        macd = ema_fast - ema_slow if (ema_fast is not None and ema_slow is not None) else pd.Series(index=df.index, dtype=float)
        macd_signal = macd.ewm(span=9, adjust=False).mean() if (n >= 9 and macd is not None) else pd.Series(index=df.index, dtype=float)
        sma_20 = close.rolling(window=20, min_periods=20).mean() if n >= 20 else pd.Series(index=df.index, dtype=float)
        sma_50 = close.rolling(window=50, min_periods=50).mean() if n >= 50 else pd.Series(index=df.index, dtype=float)
        rolling_mean = close.rolling(window=20, min_periods=20).mean() if n >= 20 else None
        rolling_std = close.rolling(window=20, min_periods=20).std() if n >= 20 else None
        bollinger_upper = rolling_mean + (2 * rolling_std) if rolling_mean is not None else pd.Series(index=df.index, dtype=float)
        bollinger_lower = rolling_mean - (2 * rolling_std) if rolling_mean is not None else pd.Series(index=df.index, dtype=float)
        atr = _fallback_atr(df) if n >= 14 else pd.Series(index=df.index, dtype=float)

    indicators = pd.DataFrame(
        {
            "timestamp": df["timestamp"],
            "rsi": rsi,
            "macd": macd,
            "macd_signal": macd_signal,
            "sma_20": sma_20,
            "sma_50": sma_50,
            "bollinger_upper": bollinger_upper,
            "bollinger_lower": bollinger_lower,
            "volatility": atr / close.replace(0, np.nan),
            "volume_momentum": volume.pct_change(periods=5),
        }
    )
    return indicators.replace({np.nan: None})


def indicator_rows_from_prices(stock_id: str, price_rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    prices = pd.DataFrame(price_rows)
    indicators = compute_technical_indicators(prices)
    rows: list[dict[str, Any]] = []
    for row in indicators.to_dict(orient="records"):
        rows.append(
            {
                "stock_id": stock_id,
                "timestamp": row["timestamp"].isoformat(),
                **{column: row.get(column) for column in INDICATOR_COLUMNS},
            }
        )
    return rows


def recalculate_indicators(
    repository: SupabaseRepository | None = None,
    stock_ids: Iterable[str] | None = None,
    price_limit: int = 300,
) -> dict[str, int]:
    repository = repository or SupabaseRepository()
    if stock_ids is None:
        stock_ids = [stock["id"] for stock in repository.list_stocks()]

    indicator_rows: list[dict[str, Any]] = []
    for stock_id in stock_ids:
        prices = repository.get_prices(stock_id, limit=price_limit)
        if prices:
            indicator_rows.extend(indicator_rows_from_prices(stock_id, prices))

    stored = repository.upsert_indicators(indicator_rows)
    return {"indicators": len(stored)}

