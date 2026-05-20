from __future__ import annotations

import numpy as np
import pandas as pd

from backend.core.math_utils import clamp
from backend.models.base import ModelPrediction, confidence_from_history, latest_timestamp


class EarningsDriftModel:
    name = "earnings_drift"

    def predict(
        self,
        stock_id: str,
        prices: pd.DataFrame,
        indicators: pd.DataFrame,
    ) -> ModelPrediction:
        if prices.empty:
            return ModelPrediction(stock_id, "", self.name, 0.5, 0.0, 0.1)

        close = pd.to_numeric(prices["close"], errors="coerce")
        short_return = close.pct_change(5).iloc[-1] if len(close) > 5 else 0.0
        medium_return = close.pct_change(20).iloc[-1] if len(close) > 20 else 0.0
        drift = float(np.nan_to_num((0.65 * short_return) + (0.35 * medium_return)))

        probability_up = clamp(0.5 + np.tanh(drift * 8.0) * 0.18)
        expected_return = float(np.tanh(drift * 3.0) * 0.06)
        confidence = confidence_from_history(prices, base=0.25)
        return ModelPrediction(
            stock_id=stock_id,
            timestamp=latest_timestamp(prices, indicators),
            model_name=self.name,
            probability_up=probability_up,
            expected_return=expected_return,
            confidence=confidence,
        )

