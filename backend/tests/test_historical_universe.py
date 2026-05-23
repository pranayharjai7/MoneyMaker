from __future__ import annotations

import pytest

from backend.historical_universe.service import bootstrap_all_universes, describe_universes, sync_universe
from backend.historical_universe.universes import (
    REQUIRED_ETFS,
    UNIVERSE_DEFINITIONS,
    get_universe_definition,
    list_universe_slugs,
)


class FakeUniverseRepository:
    def __init__(self) -> None:
        self.stocks: list[dict] = []
        self.universes: dict[str, dict] = {}
        self.memberships: dict[str, list[str]] = {}

    def upsert_stocks(self, stocks: list[dict]) -> list[dict]:
        for stock in stocks:
            ticker = stock["ticker"]
            existing = next((row for row in self.stocks if row["ticker"] == ticker), None)
            if existing:
                continue
            self.stocks.append({**stock, "id": f"stock-{ticker}"})
        return [row for row in self.stocks if row["ticker"] in {s["ticker"] for s in stocks}]

    def list_stocks(self) -> list[dict]:
        return self.stocks

    def upsert_stock_universe(self, name: str, description: str | None = None) -> dict:
        row = {
            "id": f"universe-{name}",
            "name": name,
            "description": description,
        }
        self.universes[name] = row
        return row

    def replace_universe_memberships(self, universe_id: str, stock_ids: list[str]) -> list[dict]:
        self.memberships[universe_id] = list(stock_ids)
        return [{"universe_id": universe_id, "stock_id": sid} for sid in stock_ids]

    def get_stock_universe_by_name(self, name: str) -> dict | None:
        return self.universes.get(name)

    def list_universe_members(self, universe_id: str) -> list[dict]:
        return [
            {"added_at": "2026-01-01T00:00:00+00:00", "stocks": stock}
            for stock in self.stocks
            if f"stock-{stock['ticker']}" in self.memberships.get(universe_id, [])
        ]


def test_required_etfs_present_in_definitions() -> None:
    for slug in ("core_large_cap", "etf_only", "high_liquidity"):
        tickers = set(get_universe_definition(slug).tickers)
        for etf in REQUIRED_ETFS:
            assert etf in tickers, f"{etf} missing from {slug}"


def test_all_universe_slugs_registered() -> None:
    assert set(list_universe_slugs()) == set(UNIVERSE_DEFINITIONS.keys())
    assert len(list_universe_slugs()) == 4


def test_core_large_cap_includes_sp100_sample() -> None:
    tickers = set(get_universe_definition("core_large_cap").tickers)
    for symbol in ("AAPL", "MSFT", "JPM", "XOM", "NVDA"):
        assert symbol in tickers


def test_sync_universe_upserts_stocks_and_memberships() -> None:
    repo = FakeUniverseRepository()
    result = sync_universe("etf_only", repository=repo)

    assert result["stocks"] == len(get_universe_definition("etf_only").tickers)
    assert result["memberships"] == result["stocks"]
    assert repo.universes["etf_only"]["description"]
    assert len(repo.stocks) == result["stocks"]


def test_bootstrap_all_universes_syncs_every_slug() -> None:
    repo = FakeUniverseRepository()
    results = bootstrap_all_universes(repository=repo)

    assert set(results.keys()) == set(list_universe_slugs())
    assert all(counts["memberships"] > 0 for counts in results.values())


def test_describe_universes_returns_catalog() -> None:
    catalog = describe_universes()
    assert len(catalog) == 4
    assert all("name" in row and "ticker_count" in row for row in catalog)


def test_unknown_universe_raises() -> None:
    with pytest.raises(KeyError, match="Unknown universe"):
        get_universe_definition("invalid_slug")
