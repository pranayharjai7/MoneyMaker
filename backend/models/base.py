from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pandas as pd
import numpy as np

from backend.core.math_utils import clamp, safe_float


@dataclass(frozen=True)
class ModelPrediction:
    stock_id: str
    timestamp: str
    model_name: str
    probability_up: float
    expected_return: float
    confidence: float

    def to_row(self) -> dict[str, object]:
        return {
            "stock_id": self.stock_id,
            "timestamp": self.timestamp,
            "model_name": self.model_name,
            "probability_up": clamp(self.probability_up),
            "expected_return": safe_float(self.expected_return),
            "confidence": clamp(self.confidence),
        }


class TradingModel(Protocol):
    name: str

    def predict(
        self,
        stock_id: str,
        prices: pd.DataFrame,
        indicators: pd.DataFrame,
    ) -> ModelPrediction:
        ...


def sigmoid(value: float) -> float:
    value = max(-50.0, min(50.0, value))
    return 1.0 / (1.0 + float(np.exp(-value)))


def latest_timestamp(prices: pd.DataFrame, indicators: pd.DataFrame) -> str:
    source = indicators if not indicators.empty else prices
    timestamp = pd.to_datetime(source.iloc[-1]["timestamp"], utc=True)
    return timestamp.isoformat()


def latest_close(prices: pd.DataFrame) -> float:
    if prices.empty:
        return 0.0
    return safe_float(prices.iloc[-1].get("close"))


def confidence_from_history(prices: pd.DataFrame, base: float = 0.35) -> float:
    history_factor = min(len(prices) / 120.0, 1.0) * 0.35
    return clamp(base + history_factor)
