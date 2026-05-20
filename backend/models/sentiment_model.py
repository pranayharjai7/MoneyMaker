from __future__ import annotations

import numpy as np
import pandas as pd

from backend.core.math_utils import clamp, safe_float
from backend.models.base import ModelPrediction, confidence_from_history, latest_timestamp


class SentimentModel:
    name = "sentiment"

    def predict(
        self,
        stock_id: str,
        prices: pd.DataFrame,
        indicators: pd.DataFrame,
    ) -> ModelPrediction:
        if prices.empty:
            return ModelPrediction(stock_id, "", self.name, 0.5, 0.0, 0.1)

        latest_indicator = indicators.iloc[-1] if not indicators.empty else {}
        sentiment_score = safe_float(getattr(latest_indicator, "get", lambda *_: 0.0)("sentiment_score"))
        if sentiment_score == 0.0 and len(prices) > 3:
            recent_return = pd.to_numeric(prices["close"], errors="coerce").pct_change(3).iloc[-1]
            sentiment_score = float(np.nan_to_num(np.tanh(recent_return * 5.0))) * 0.25

        probability_up = clamp(0.5 + (np.tanh(sentiment_score) * 0.24))
        expected_return = float(np.tanh(sentiment_score) * 0.05)
        confidence = confidence_from_history(prices, base=0.22)
        return ModelPrediction(
            stock_id=stock_id,
            timestamp=latest_timestamp(prices, indicators),
            model_name=self.name,
            probability_up=probability_up,
            expected_return=expected_return,
            confidence=confidence,
        )

