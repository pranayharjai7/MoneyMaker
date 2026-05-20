from __future__ import annotations

import numpy as np
import pandas as pd

from backend.core.math_utils import clamp, safe_float
from backend.models.base import ModelPrediction, confidence_from_history, latest_close, latest_timestamp


class VolatilityBreakoutModel:
    name = "volatility_breakout"

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
        upper = safe_float(row.get("bollinger_upper"), close)
        lower = safe_float(row.get("bollinger_lower"), close)
        volatility = safe_float(row.get("volatility"), 0.02)
        volume_momentum = safe_float(row.get("volume_momentum"))

        upper_breakout = (close / max(upper, 1e-9)) - 1.0
        lower_breakout = (close / max(lower, 1e-9)) - 1.0
        directional_breakout = max(upper_breakout, 0.0) + min(lower_breakout, 0.0)
        volume_boost = np.tanh(volume_momentum)
        score = np.tanh((directional_breakout * 35.0) + (volume_boost * 0.35))

        probability_up = clamp(0.5 + (score * 0.3))
        expected_return = float(score * min(max(volatility * 3.0, 0.01), 0.12))
        confidence = clamp(confidence_from_history(prices, base=0.35) + min(abs(volume_boost) * 0.1, 0.1))
        return ModelPrediction(
            stock_id=stock_id,
            timestamp=latest_timestamp(prices, indicators),
            model_name=self.name,
            probability_up=probability_up,
            expected_return=expected_return,
            confidence=confidence,
        )

