from __future__ import annotations

import pandas as pd

from backend.features.indicators import compute_technical_indicators
from backend.models.registry import get_default_models


def test_default_models_emit_valid_probabilities() -> None:
    prices = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=90, freq="D", tz="UTC"),
            "open": [100 + index * 0.5 for index in range(90)],
            "high": [101 + index * 0.5 for index in range(90)],
            "low": [99 + index * 0.5 for index in range(90)],
            "close": [100.5 + index * 0.5 for index in range(90)],
            "volume": [1_000_000 + (index * 5_000) for index in range(90)],
        }
    )
    indicators = compute_technical_indicators(prices)

    for model in get_default_models():
        prediction = model.predict("stock-1", prices, indicators)
        row = prediction.to_row()
        assert row["model_name"]
        assert 0 <= row["probability_up"] <= 1
        assert 0 <= row["confidence"] <= 1

