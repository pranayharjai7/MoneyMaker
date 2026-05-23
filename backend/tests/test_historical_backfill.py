from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from backend.core.config import Settings
from backend.data_pipeline.providers import PriceBar
from backend.historical_backfill.chunks import (
    chunk_is_fully_covered,
    compute_backfill_window,
    iter_date_chunks,
)
from backend.historical_backfill.fetcher import ProviderFetchError, fetch_prices_with_failover
from backend.historical_backfill.service import backfill_ticker
from backend.reliability.retry import RetryPolicy


class FakeProvider:
    def __init__(self, name: str, bars: list[PriceBar] | None = None, *, fail: bool = False) -> None:
        self.name = name
        self.bars = bars or []
        self.fail = fail
        self.calls = 0

    async def fetch_stock_list(self) -> list:
        return []

    async def fetch_historical_prices(self, ticker: str, start_date: date, end_date: date) -> list[PriceBar]:
        self.calls += 1
        if self.fail:
            raise RuntimeError(f"{self.name} unavailable")
        return [
            bar
            for bar in self.bars
            if start_date <= bar.timestamp.date() <= end_date
        ]


class FakeBackfillRepository:
    def __init__(self) -> None:
        self.stocks: dict[str, dict] = {}
        self.prices: list[dict] = []
        self.backfill_state: dict[tuple[str, str], dict] = {}

    def get_stock_by_ticker(self, ticker: str) -> dict | None:
        return self.stocks.get(ticker.upper())

    def upsert_stocks(self, stocks: list[dict]) -> list[dict]:
        for stock in stocks:
            ticker = stock["ticker"]
            self.stocks[ticker] = {**stock, "id": f"stock-{ticker}"}
        return list(self.stocks.values())

    def upsert_prices(self, prices: list[dict]) -> list[dict]:
        for row in prices:
            key = (row["stock_id"], row["timestamp"])
            if not any((p["stock_id"], p["timestamp"]) == key for p in self.prices):
                self.prices.append(row)
        return prices

    def get_price_backfill_state(self, stock_id: str, *, resolution: str = "daily") -> dict | None:
        return self.backfill_state.get((stock_id, resolution))

    def upsert_price_backfill_state(self, **kwargs) -> dict:
        key = (kwargs["stock_id"], kwargs["resolution"])
        self.backfill_state[key] = kwargs
        return kwargs


def _bar(day: str, close: float = 100.0) -> PriceBar:
    parsed = date.fromisoformat(day)
    return PriceBar(
        ticker="SPY",
        timestamp=datetime.combine(parsed, datetime.min.time(), tzinfo=timezone.utc),
        open=close,
        high=close + 1,
        low=close - 1,
        close=close,
        volume=1_000_000,
    )


def test_iter_date_chunks_year_granularity() -> None:
    chunks = iter_date_chunks(date(2021, 6, 15), date(2023, 2, 1), granularity="year")
    assert chunks == [
        (date(2021, 6, 15), date(2021, 12, 31)),
        (date(2022, 1, 1), date(2022, 12, 31)),
        (date(2023, 1, 1), date(2023, 2, 1)),
    ]


def test_iter_date_chunks_month_granularity() -> None:
    chunks = iter_date_chunks(date(2024, 11, 10), date(2025, 1, 5), granularity="month")
    assert len(chunks) == 3
    assert chunks[0] == (date(2024, 11, 10), date(2024, 11, 30))
    assert chunks[-1] == (date(2025, 1, 1), date(2025, 1, 5))


def test_chunk_is_fully_covered() -> None:
    assert not chunk_is_fully_covered(date(2020, 1, 1), date(2020, 12, 31), None)
    assert chunk_is_fully_covered(date(2020, 1, 1), date(2020, 12, 31), date(2020, 12, 31))
    assert not chunk_is_fully_covered(date(2021, 1, 1), date(2021, 12, 31), date(2020, 12, 31))


def test_compute_backfill_window_five_years() -> None:
    start, end = compute_backfill_window(years=5, end_date=date(2026, 5, 22))
    assert end == date(2026, 5, 22)
    assert (end - start).days >= 5 * 365 - 1


@pytest.mark.asyncio
async def test_fetch_prices_with_failover_switches_provider() -> None:
    failing = FakeProvider("polygon", fail=True)
    working = FakeProvider("finnhub", bars=[_bar("2024-01-02")])
    bars, provider = await fetch_prices_with_failover(
        "SPY",
        date(2024, 1, 1),
        date(2024, 1, 31),
        providers=[failing, working],
        provider_cooldown_seconds=0,
    )
    assert provider == "finnhub"
    assert len(bars) == 1
    assert failing.calls == 3
    assert working.calls == 1


@pytest.mark.asyncio
async def test_fetch_prices_with_failover_raises_when_all_fail() -> None:
    providers = [FakeProvider("polygon", fail=True), FakeProvider("finnhub", fail=True)]
    with pytest.raises(ProviderFetchError):
        await fetch_prices_with_failover(
            "SPY",
            date(2024, 1, 1),
            date(2024, 1, 31),
            providers=providers,
            retry_policy=RetryPolicy(max_attempts=1),
        )


@pytest.mark.asyncio
async def test_backfill_ticker_stores_real_bars_and_skips_completed_chunks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bars = [
        _bar("2022-01-03", 400),
        _bar("2022-06-01", 410),
        _bar("2023-01-04", 420),
    ]

    async def fake_fetch(ticker, start_date, end_date, **kwargs):
        filtered = [b for b in bars if start_date <= b.timestamp.date() <= end_date]
        return filtered, "polygon"

    monkeypatch.setattr(
        "backend.historical_backfill.service.fetch_prices_with_failover",
        fake_fetch,
    )

    repo = FakeBackfillRepository()
    repo.upsert_stocks([{"ticker": "SPY", "company_name": "SPY", "exchange": "US"}])

    settings = Settings(
        historical_backfill_years=2,
        historical_backfill_chunk_granularity="year",
        historical_backfill_provider_cooldown_seconds=0,
    )
    first = await backfill_ticker(
        "SPY",
        start_date=date(2022, 1, 1),
        end_date=date(2023, 12, 31),
        repository=repo,
        settings=settings,
    )
    assert first.status == "completed"
    assert first.bars_stored == 3
    assert len(repo.prices) == 3

    second = await backfill_ticker(
        "SPY",
        start_date=date(2022, 1, 1),
        end_date=date(2023, 12, 31),
        repository=repo,
        settings=settings,
    )
    assert second.chunks_skipped >= 1
    assert len(repo.prices) == 3
