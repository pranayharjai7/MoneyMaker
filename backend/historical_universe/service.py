from __future__ import annotations

from typing import Any

from backend.data_pipeline.providers import StockRecord
from backend.db.repository import SupabaseRepository
from backend.historical_universe.universes import (
    UNIVERSE_DEFINITIONS,
    UniverseDefinition,
    get_universe_definition,
    list_universe_slugs,
)


def bootstrap_all_universes(
    repository: SupabaseRepository | None = None,
) -> dict[str, dict[str, int]]:
    """Ensure all predefined universes exist with current memberships."""
    repository = repository or SupabaseRepository()
    results: dict[str, dict[str, int]] = {}
    for slug in list_universe_slugs():
        results[slug] = sync_universe(slug, repository=repository)
    return results


def sync_universe(
    slug: str,
    repository: SupabaseRepository | None = None,
    extra_stocks: list[StockRecord] | None = None,
) -> dict[str, int]:
    """Upsert stocks, universe row, and memberships for one universe slug."""
    repository = repository or SupabaseRepository()
    definition = get_universe_definition(slug)
    stock_records = definition.stock_records()
    if extra_stocks:
        merged = {record.ticker.upper(): record for record in stock_records}
        for record in extra_stocks:
            merged[record.ticker.upper()] = record
        stock_records = list(merged.values())

    upserted = repository.upsert_stocks([record.to_row() for record in stock_records])
    stock_by_ticker = {row["ticker"]: row for row in upserted}
    if not stock_by_ticker:
        stock_by_ticker = {
            row["ticker"]: row
            for row in repository.list_stocks()
            if row["ticker"] in {record.ticker.upper() for record in stock_records}
        }

    universe = repository.upsert_stock_universe(
        name=definition.slug,
        description=definition.description,
    )
    stock_ids = [
        stock_by_ticker[record.ticker.upper()]["id"]
        for record in stock_records
        if record.ticker.upper() in stock_by_ticker
    ]
    memberships = repository.replace_universe_memberships(universe["id"], stock_ids)
    return {
        "stocks": len(stock_ids),
        "memberships": len(memberships),
    }


def list_universe_members(
    slug: str,
    repository: SupabaseRepository | None = None,
) -> list[dict[str, Any]]:
    """Return stocks in a universe with membership metadata."""
    repository = repository or SupabaseRepository()
    universe = repository.get_stock_universe_by_name(slug)
    if not universe:
        return []
    return repository.list_universe_members(universe["id"])


def describe_universes() -> list[dict[str, Any]]:
    """Static catalog of configured universe definitions (no DB required)."""
    return [
        {
            "name": definition.slug,
            "description": definition.description,
            "ticker_count": len(definition.tickers),
            "sample_tickers": list(definition.tickers[:8]),
        }
        for definition in UNIVERSE_DEFINITIONS.values()
    ]
