from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
from typing import Any

import pandas as pd

from backend.db.repository import SupabaseRepository
from backend.historical_features.compute import HISTORICAL_FEATURE_COLUMNS


def _to_utc_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value)
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _day_start(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=UTC)


def _frame(rows: list[dict[str, Any]], columns: list[str]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=columns)
    frame = pd.DataFrame(rows)
    if "timestamp" in frame.columns:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        frame = frame.sort_values("timestamp").reset_index(drop=True)
    return frame


@dataclass
class StockSeries:
    stock_id: str
    ticker: str
    prices: pd.DataFrame
    features: pd.DataFrame

    def slice_before(self, as_of: datetime) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Return only rows strictly before as_of (no future leakage)."""
        price_slice = self.prices[self.prices["timestamp"] < as_of]
        feature_slice = self.features[self.features["timestamp"] < as_of]
        return price_slice.reset_index(drop=True), feature_slice.reset_index(drop=True)

    def price_at_or_after(self, as_of: datetime) -> dict[str, Any] | None:
        rows = self.prices[self.prices["timestamp"] >= as_of]
        if rows.empty:
            return None
        return rows.iloc[0].to_dict()


@dataclass
class ReplayDataset:
    """In-memory OHLCV + features for replay (loaded once per run)."""

    benchmark_ticker: str
    stocks: dict[str, StockSeries]
    trading_days: list[date] = field(default_factory=list)
    _benchmark_prices: pd.DataFrame = field(default_factory=pd.DataFrame)

    @classmethod
    def load(
        cls,
        repository: SupabaseRepository,
        *,
        stock_ids: list[str],
        tickers_by_id: dict[str, str],
        start_date: date,
        end_date: date,
        benchmark_ticker: str = "SPY",
        price_limit: int = 50_000,
    ) -> ReplayDataset:
        start_ts = _day_start(start_date).isoformat()
        end_ts = _day_start(end_date).isoformat()

        stocks: dict[str, StockSeries] = {}
        for stock_id in stock_ids:
            ticker = tickers_by_id.get(stock_id, stock_id)
            prices = repository.get_prices_in_range(
                stock_id,
                start_timestamp=start_ts,
                end_timestamp=end_ts,
                limit=price_limit,
            )
            features = repository.get_historical_features(
                stock_id,
                start_timestamp=start_ts,
                end_timestamp=end_ts,
                limit=price_limit,
            )
            if not prices:
                continue
            indicator_columns = ["timestamp", *HISTORICAL_FEATURE_COLUMNS]
            stocks[stock_id] = StockSeries(
                stock_id=stock_id,
                ticker=ticker,
                prices=_frame(prices, ["timestamp", "open", "high", "low", "close", "volume"]),
                features=_frame(features, indicator_columns),
            )

        benchmark_id = next(
            (sid for sid, ticker in tickers_by_id.items() if ticker.upper() == benchmark_ticker.upper()),
            None,
        )
        benchmark_prices = pd.DataFrame()
        if benchmark_id and benchmark_id in stocks:
            benchmark_prices = stocks[benchmark_id].prices.copy()

        trading_days = cls._derive_trading_days(benchmark_prices, start_date, end_date)
        return cls(
            benchmark_ticker=benchmark_ticker,
            stocks=stocks,
            trading_days=trading_days,
            _benchmark_prices=benchmark_prices,
        )

    @staticmethod
    def _derive_trading_days(
        benchmark_prices: pd.DataFrame,
        start_date: date,
        end_date: date,
    ) -> list[date]:
        if benchmark_prices.empty:
            return []
        days = sorted(
            {
                _to_utc_datetime(value).date()
                for value in benchmark_prices["timestamp"].tolist()
                if start_date <= _to_utc_datetime(value).date() <= end_date
            }
        )
        return days

    def benchmark_slice_before(self, as_of: datetime) -> pd.DataFrame:
        if self._benchmark_prices.empty:
            return self._benchmark_prices
        return self._benchmark_prices[self._benchmark_prices["timestamp"] < as_of].reset_index(drop=True)
