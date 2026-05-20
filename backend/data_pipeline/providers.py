from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Protocol

import httpx

from backend.core.config import Settings


@dataclass(frozen=True)
class StockRecord:
    ticker: str
    company_name: str
    sector: str | None = None
    exchange: str | None = None

    def to_row(self) -> dict[str, object]:
        return {
            "ticker": self.ticker.upper(),
            "company_name": self.company_name,
            "sector": self.sector,
            "exchange": self.exchange,
        }


@dataclass(frozen=True)
class PriceBar:
    ticker: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    def to_row(self, stock_id: str) -> dict[str, object]:
        return {
            "stock_id": stock_id,
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


class MarketDataProvider(Protocol):
    name: str

    async def fetch_stock_list(self) -> list[StockRecord]:
        ...

    async def fetch_historical_prices(
        self, ticker: str, start_date: date, end_date: date
    ) -> list[PriceBar]:
        ...


class ProviderNotConfiguredError(RuntimeError):
    pass


def _market_close_utc(day: date) -> datetime:
    return datetime.combine(day, time(hour=21), tzinfo=timezone.utc)


class AlphaVantageProvider:
    name = "alpha_vantage"

    def __init__(self, api_key: str | None, timeout: float = 20.0):
        if not api_key:
            raise ProviderNotConfiguredError("ALPHA_VANTAGE_API_KEY is not configured")
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = "https://www.alphavantage.co/query"

    async def fetch_stock_list(self) -> list[StockRecord]:
        return []

    async def fetch_historical_prices(
        self, ticker: str, start_date: date, end_date: date
    ) -> list[PriceBar]:
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": ticker.upper(),
            "outputsize": "full",
            "apikey": self.api_key,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            payload = response.json()

        series = payload.get("Time Series (Daily)", {})
        bars: list[PriceBar] = []
        for day_text, values in series.items():
            day = date.fromisoformat(day_text)
            if not start_date <= day <= end_date:
                continue
            bars.append(
                PriceBar(
                    ticker=ticker.upper(),
                    timestamp=_market_close_utc(day),
                    open=float(values["1. open"]),
                    high=float(values["2. high"]),
                    low=float(values["3. low"]),
                    close=float(values["4. close"]),
                    volume=float(values["6. volume"]),
                )
            )
        return sorted(bars, key=lambda bar: bar.timestamp)


class FinnhubProvider:
    name = "finnhub"

    def __init__(self, api_key: str | None, timeout: float = 20.0):
        if not api_key:
            raise ProviderNotConfiguredError("FINNHUB_API_KEY is not configured")
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = "https://finnhub.io/api/v1"

    async def fetch_stock_list(self) -> list[StockRecord]:
        params = {"exchange": "US", "token": self.api_key}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/stock/symbol", params=params)
            response.raise_for_status()
            payload = response.json()
        return [
            StockRecord(
                ticker=item["symbol"].upper(),
                company_name=item.get("description") or item["symbol"].upper(),
                exchange=item.get("mic") or "US",
            )
            for item in payload
            if item.get("symbol") and item.get("type") in {None, "Common Stock", "ETP"}
        ]

    async def fetch_historical_prices(
        self, ticker: str, start_date: date, end_date: date
    ) -> list[PriceBar]:
        params = {
            "symbol": ticker.upper(),
            "resolution": "D",
            "from": int(datetime.combine(start_date, time.min, timezone.utc).timestamp()),
            "to": int(datetime.combine(end_date, time.max, timezone.utc).timestamp()),
            "token": self.api_key,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/stock/candle", params=params)
            response.raise_for_status()
            payload = response.json()

        if payload.get("s") != "ok":
            return []
        bars = []
        for index, epoch in enumerate(payload.get("t", [])):
            bars.append(
                PriceBar(
                    ticker=ticker.upper(),
                    timestamp=datetime.fromtimestamp(epoch, timezone.utc),
                    open=float(payload["o"][index]),
                    high=float(payload["h"][index]),
                    low=float(payload["l"][index]),
                    close=float(payload["c"][index]),
                    volume=float(payload["v"][index]),
                )
            )
        return bars


class PolygonProvider:
    name = "polygon"

    def __init__(self, api_key: str | None, timeout: float = 20.0):
        if not api_key:
            raise ProviderNotConfiguredError("POLYGON_API_KEY is not configured")
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = "https://api.polygon.io"

    async def fetch_stock_list(self) -> list[StockRecord]:
        params = {
            "market": "stocks",
            "active": "true",
            "limit": 1000,
            "apiKey": self.api_key,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/v3/reference/tickers", params=params)
            response.raise_for_status()
            payload = response.json()
        return [
            StockRecord(
                ticker=item["ticker"].upper(),
                company_name=item.get("name") or item["ticker"].upper(),
                exchange=item.get("primary_exchange"),
            )
            for item in payload.get("results", [])
            if item.get("ticker")
        ]

    async def fetch_historical_prices(
        self, ticker: str, start_date: date, end_date: date
    ) -> list[PriceBar]:
        path = (
            f"{self.base_url}/v2/aggs/ticker/{ticker.upper()}/range/1/day/"
            f"{start_date.isoformat()}/{end_date.isoformat()}"
        )
        params = {"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": self.api_key}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(path, params=params)
            response.raise_for_status()
            payload = response.json()
        bars = []
        for item in payload.get("results", []):
            bars.append(
                PriceBar(
                    ticker=ticker.upper(),
                    timestamp=datetime.fromtimestamp(item["t"] / 1000, timezone.utc),
                    open=float(item["o"]),
                    high=float(item["h"]),
                    low=float(item["l"]),
                    close=float(item["c"]),
                    volume=float(item.get("v", 0)),
                )
            )
        return bars


def configured_providers(settings: Settings) -> list[MarketDataProvider]:
    providers: list[MarketDataProvider] = []
    for provider_cls, api_key in (
        (PolygonProvider, settings.polygon_api_key),
        (FinnhubProvider, settings.finnhub_api_key),
        (AlphaVantageProvider, settings.alpha_vantage_api_key),
    ):
        try:
            providers.append(provider_cls(api_key, settings.market_data_timeout_seconds))
        except ProviderNotConfiguredError:
            continue
    return providers

