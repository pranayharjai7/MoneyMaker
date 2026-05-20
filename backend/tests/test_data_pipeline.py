from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from backend.core.config import Settings
from backend.data_pipeline.providers import PriceBar, StockRecord
from backend.data_pipeline.service import update_daily_prices


class FakeRepository:
    def __init__(self) -> None:
        self.stocks: list[dict] = []
        self.prices: list[dict] = []

    def upsert_stocks(self, stocks: list[dict]) -> list[dict]:
        self.stocks = [{**stock, "id": f"stock-{stock['ticker']}"} for stock in stocks]
        return self.stocks

    def list_stocks(self) -> list[dict]:
        return self.stocks

    def upsert_prices(self, prices: list[dict]) -> list[dict]:
        self.prices = prices
        return prices


def test_update_daily_prices_stores_stock_and_price_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_stock_list(settings=None):
        return [StockRecord(ticker="AAPL", company_name="Apple Inc.", exchange="NASDAQ")]

    async def fake_prices(ticker, start_date=None, end_date=None, settings=None):
        return [
            PriceBar(
                ticker=ticker,
                timestamp=datetime(2026, 5, 19, 21, tzinfo=timezone.utc),
                open=190,
                high=195,
                low=188,
                close=194,
                volume=10_000_000,
            )
        ]

    monkeypatch.setattr("backend.data_pipeline.service.fetch_stock_list", fake_stock_list)
    monkeypatch.setattr("backend.data_pipeline.service.fetch_historical_prices", fake_prices)

    repo = FakeRepository()
    result = asyncio.run(
        update_daily_prices(
            tickers=["AAPL"],
            repository=repo,
            settings=Settings(default_tickers="AAPL"),
            lookback_days=3,
        )
    )

    assert result == {"stocks": 1, "prices": 1}
    assert repo.stocks[0]["ticker"] == "AAPL"
    assert repo.prices[0]["stock_id"] == "stock-AAPL"
