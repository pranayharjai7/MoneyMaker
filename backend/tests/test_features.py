from __future__ import annotations

import pandas as pd

from backend.features.indicators import INDICATOR_COLUMNS, compute_technical_indicators


def test_compute_technical_indicators_returns_expected_columns() -> None:
    prices = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=80, freq="D", tz="UTC"),
            "open": [100 + index for index in range(80)],
            "high": [102 + index for index in range(80)],
            "low": [99 + index for index in range(80)],
            "close": [101 + index for index in range(80)],
            "volume": [1_000_000 + (index * 1_000) for index in range(80)],
        }
    )

    indicators = compute_technical_indicators(prices)

    assert list(indicators.columns) == ["timestamp", *INDICATOR_COLUMNS]
    assert len(indicators) == 80
    assert indicators.iloc[-1]["sma_20"] is not None
    assert indicators.iloc[-1]["volatility"] is not None

