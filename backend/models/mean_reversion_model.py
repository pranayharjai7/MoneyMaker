from __future__ import annotations

import numpy as np
import pandas as pd

from backend.core.math_utils import clamp, safe_float
from backend.models.base import ModelPrediction, confidence_from_history, latest_close, latest_timestamp


class MeanReversionModel:
    name = "mean_reversion"

    def predict(
        self,
        stock_id: str,
        prices: pd.DataFrame,
        indicators: pd.DataFrame,
    ) -> ModelPrediction:
        if prices.empty or indicators.empty:
            return ModelPrediction(stock_id, "", self.name, 0.5, 0.0, 0.1)

        row = indicators.iloc[-1]
        close = latest_close(prices)
        rsi = safe_float(row.get("rsi"), 50.0)
        sma_20 = safe_float(row.get("sma_20"), close)
        upper = safe_float(row.get("bollinger_upper"), close)
        lower = safe_float(row.get("bollinger_lower"), close)
        band_width = max(upper - lower, 1e-9)
        band_position = (close - lower) / band_width

        oversold = max(0.0, (35.0 - rsi) / 35.0) + max(0.0, 0.35 - band_position)
        overbought = max(0.0, (rsi - 65.0) / 35.0) + max(0.0, band_position - 0.65)
        score = oversold - overbought
        probability_up = clamp(0.5 + (score * 0.22))
        expected_return = float(np.tanh((sma_20 / max(close, 1e-9)) - 1.0) * 0.09)
        confidence = confidence_from_history(prices, base=0.38)
        return ModelPrediction(
            stock_id=stock_id,
            timestamp=latest_timestamp(prices, indicators),
            model_name=self.name,
            probability_up=probability_up,
            expected_return=expected_return,
            confidence=confidence,
        )

