from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from backend.historical_features.compute import compute_historical_features, sector_etf_for_stock
from backend.historical_features.service import generate_features_for_stock


def _synthetic_price_series(days: int = 120, start: float = 100.0) -> list[dict]:
    """Deterministic OHLCV path for tests (derived from real-style structure, not random returns)."""
    rows: list[dict] = []
    price = start
    base = datetime(2023, 1, 3, 21, tzinfo=timezone.utc)
    for index in range(days):
        drift = 0.0015 if index % 5 else -0.0005
        price = max(1.0, price * (1 + drift))
        day = base + timedelta(days=index)
        rows.append(
            {
                "timestamp": day.isoformat(),
                "open": price * 0.995,
                "high": price * 1.01,
                "low": price * 0.99,
                "close": price,
                "volume": 1_000_000 + index * 1000,
            }
        )
    return rows


def test_compute_historical_features_includes_advanced_columns() -> None:
    prices = _synthetic_price_series(130)
    benchmark = _synthetic_price_series(130, start=400.0)
    features = compute_historical_features(prices, benchmark_rows=benchmark, sector_rows=benchmark)
    for column in (
        "atr",
        "rolling_beta_spy",
        "sector_relative_strength",
        "volatility_percentile",
        "trend_persistence",
    ):
        assert column in features.columns
    assert features["rsi"].notna().sum() > 0


def test_no_future_leakage_at_cutoff() -> None:
    prices = _synthetic_price_series(100)
    benchmark = _synthetic_price_series(100, start=400.0)
    cutoff = 70

    full = compute_historical_features(prices, benchmark_rows=benchmark)
    partial = compute_historical_features(prices[:cutoff], benchmark_rows=benchmark[:cutoff])

    compare_columns = ["rsi", "rolling_beta_spy", "volatility_percentile", "trend_persistence"]
    for column in compare_columns:
        full_value = full.iloc[cutoff - 1][column]
        partial_value = partial.iloc[cutoff - 1][column]
        if full_value is None or partial_value is None:
            continue
        assert full_value == pytest.approx(partial_value, rel=1e-6, abs=1e-6)


def test_sector_etf_mapping_defaults_to_spy() -> None:
    assert sector_etf_for_stock({"sector": "Technology"}) == "XLK"
    assert sector_etf_for_stock({"sector": "Unknown Sector"}) == "SPY"
    assert sector_etf_for_stock(None) == "SPY"


class FakeFeatureRepository:
    def __init__(self) -> None:
        self.stocks = {"stock-1": {"id": "stock-1", "ticker": "AAPL", "sector": "Technology"}}
        self.prices: dict[str, list[dict]] = {}
        self.features: list[dict] = []

    def get_stock(self, stock_id: str) -> dict | None:
        return self.stocks.get(stock_id)

    def get_prices_in_range(self, stock_id: str, **kwargs) -> list[dict]:
        return self.prices.get(stock_id, [])

    def get_prices_for_ticker(self, ticker: str, limit: int = 50_000) -> list[dict]:
        for stock in self.stocks.values():
            if stock["ticker"] == ticker:
                return self.prices.get(stock["id"], [])
        if ticker == "SPY":
            return self.prices.get("spy", [])
        if ticker == "XLK":
            return self.prices.get("xlk", [])
        return []

    def upsert_historical_features(self, rows: list[dict]) -> list[dict]:
        self.features.extend(rows)
        return rows


def test_generate_features_for_stock_persists_rows() -> None:
    repo = FakeFeatureRepository()
    series = _synthetic_price_series(90)
    repo.prices["stock-1"] = series
    repo.prices["spy"] = _synthetic_price_series(90, start=400.0)
    repo.prices["xlk"] = _synthetic_price_series(90, start=200.0)

    result = generate_features_for_stock("stock-1", repository=repo)
    assert result["features"] == 90
    assert len(repo.features) == 90
