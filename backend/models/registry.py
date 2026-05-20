from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd

from backend.db.repository import SupabaseRepository
from backend.models.base import TradingModel
from backend.models.earnings_drift_model import EarningsDriftModel
from backend.models.mean_reversion_model import MeanReversionModel
from backend.models.momentum_model import MomentumModel
from backend.models.sentiment_model import SentimentModel
from backend.models.volatility_breakout_model import VolatilityBreakoutModel


def get_default_models() -> list[TradingModel]:
    return [
        MomentumModel(),
        MeanReversionModel(),
        VolatilityBreakoutModel(),
        EarningsDriftModel(),
        SentimentModel(),
    ]


def _frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    if not frame.empty and "timestamp" in frame:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        frame = frame.sort_values("timestamp").reset_index(drop=True)
    return frame


def run_model_predictions(
    repository: SupabaseRepository | None = None,
    stock_ids: Iterable[str] | None = None,
    models: list[TradingModel] | None = None,
    history_limit: int = 300,
) -> dict[str, int]:
    repository = repository or SupabaseRepository()
    models = models or get_default_models()
    if stock_ids is None:
        stock_ids = [stock["id"] for stock in repository.list_stocks()]

    rows = []
    for stock_id in stock_ids:
        prices = _frame(repository.get_prices(stock_id, limit=history_limit))
        indicators = _frame(repository.get_indicators(stock_id, limit=history_limit))
        if prices.empty:
            continue
        for model in models:
            prediction = model.predict(stock_id, prices, indicators)
            if prediction.timestamp:
                rows.append(prediction.to_row())

    stored = repository.upsert_model_predictions(rows)
    return {"predictions": len(stored)}

