from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Sequence

from backend.core.config import Settings, get_settings
from backend.data_pipeline.providers import PriceBar, StockRecord, configured_providers
from backend.db.repository import SupabaseRepository


def _default_stock_universe(settings: Settings) -> list[StockRecord]:
    return [
        StockRecord(ticker=ticker, company_name=ticker, exchange="US")
        for ticker in settings.ticker_list
    ]


async def fetch_stock_list(settings: Settings | None = None) -> list[StockRecord]:
    settings = settings or get_settings()
    for provider in configured_providers(settings):
        stocks = await provider.fetch_stock_list()
        if stocks:
            return stocks
    return _default_stock_universe(settings)


async def fetch_historical_prices(
    ticker: str,
    start_date: date | None = None,
    end_date: date | None = None,
    settings: Settings | None = None,
) -> list[PriceBar]:
    settings = settings or get_settings()
    end_date = end_date or datetime.now(tz=UTC).date()
    start_date = start_date or end_date - timedelta(days=365)

    for provider in configured_providers(settings):
        bars = await provider.fetch_historical_prices(ticker, start_date, end_date)
        if bars:
            return bars
    return []


async def update_daily_prices(
    tickers: Sequence[str] | None = None,
    repository: SupabaseRepository | None = None,
    settings: Settings | None = None,
    lookback_days: int = 7,
) -> dict[str, int]:
    settings = settings or get_settings()
    repository = repository or SupabaseRepository()

    requested_tickers = [ticker.upper() for ticker in (tickers or settings.ticker_list)]
    universe = await fetch_stock_list(settings=settings)
    stock_rows = [
        stock.to_row()
        for stock in universe
        if not requested_tickers or stock.ticker.upper() in set(requested_tickers)
    ]
    if not stock_rows:
        stock_rows = [
            StockRecord(ticker=ticker, company_name=ticker, exchange="US").to_row()
            for ticker in requested_tickers
        ]

    upserted_stocks = repository.upsert_stocks(stock_rows)
    stock_by_ticker = {stock["ticker"]: stock for stock in upserted_stocks}
    if not stock_by_ticker:
        stock_by_ticker = {
            stock["ticker"]: stock
            for stock in repository.list_stocks()
            if stock["ticker"] in requested_tickers
        }

    end_date = datetime.now(tz=UTC).date()
    start_date = end_date - timedelta(days=lookback_days)
    price_rows = []
    for ticker in requested_tickers:
        stock = stock_by_ticker.get(ticker)
        if not stock:
            continue
        bars = await fetch_historical_prices(
            ticker,
            start_date=start_date,
            end_date=end_date,
            settings=settings,
        )
        price_rows.extend(bar.to_row(stock["id"]) for bar in bars)

    stored_prices = repository.upsert_prices(price_rows)
    return {"stocks": len(stock_rows), "prices": len(stored_prices)}

