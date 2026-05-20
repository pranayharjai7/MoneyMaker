from __future__ import annotations

import numpy as np
import pandas as pd

from backend.core.math_utils import clamp, safe_float
from backend.models.base import ModelPrediction, confidence_from_history, latest_close, latest_timestamp


class MomentumModel:
    name = "momentum"

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
        macd = safe_float(row.get("macd"))
        macd_signal = safe_float(row.get("macd_signal"))
        sma_20 = safe_float(row.get("sma_20"), close)
        sma_50 = safe_float(row.get("sma_50"), close)

        rsi_component = (rsi - 50.0) / 50.0
        macd_component = np.tanh((macd - macd_signal) / max(close, 1e-9) * 100)
        trend_component = np.tanh(((sma_20 / max(sma_50, 1e-9)) - 1.0) * 20)
        score = (0.4 * rsi_component) + (0.35 * macd_component) + (0.25 * trend_component)

        probability_up = clamp(0.5 + (score * 0.28))
        expected_return = float(np.tanh(score) * 0.08)
        confidence = confidence_from_history(prices, base=0.42)
        return ModelPrediction(
            stock_id=stock_id,
            timestamp=latest_timestamp(prices, indicators),
            model_name=self.name,
            probability_up=probability_up,
            expected_return=expected_return,
            confidence=confidence,
        )

