from __future__ import annotations

from typing import Any

from backend.db.repository import SupabaseRepository
from backend.historical_features.compute import (
    HISTORICAL_FEATURE_COLUMNS,
    compute_historical_features,
    sector_etf_for_stock,
)
from backend.historical_universe.service import list_universe_members

BENCHMARK_TICKER = "SPY"
UPSERT_BATCH_SIZE = 500


def _feature_rows(stock_id: str, features_frame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in features_frame.to_dict(orient="records"):
        timestamp = record["timestamp"]
        rows.append(
            {
                "stock_id": stock_id,
                "timestamp": timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp),
                **{column: record.get(column) for column in HISTORICAL_FEATURE_COLUMNS},
            }
        )
    return rows


def generate_features_for_stock(
    stock_id: str,
    *,
    repository: SupabaseRepository | None = None,
    price_limit: int = 50_000,
) -> dict[str, int]:
    """Generate and persist historical features for one stock from stored OHLCV."""
    repository = repository or SupabaseRepository()
    stock = repository.get_stock(stock_id)
    if not stock:
        raise ValueError(f"Unknown stock_id: {stock_id}")

    prices = repository.get_prices_in_range(stock_id, limit=price_limit)
    if not prices:
        return {"features": 0, "prices": 0}

    benchmark = repository.get_prices_for_ticker(BENCHMARK_TICKER, limit=price_limit)
    sector_ticker = sector_etf_for_stock(stock)
    sector_prices = (
        repository.get_prices_for_ticker(sector_ticker, limit=price_limit)
        if sector_ticker != stock["ticker"]
        else benchmark
    )

    features = compute_historical_features(
        prices,
        benchmark_rows=benchmark,
        sector_rows=sector_prices,
    )
    rows = _feature_rows(stock_id, features)
    stored = 0
    for offset in range(0, len(rows), UPSERT_BATCH_SIZE):
        batch = rows[offset : offset + UPSERT_BATCH_SIZE]
        stored += len(repository.upsert_historical_features(batch))
    return {"features": stored, "prices": len(prices)}


def generate_features_for_ticker(
    ticker: str,
    *,
    repository: SupabaseRepository | None = None,
) -> dict[str, int]:
    repository = repository or SupabaseRepository()
    stock = repository.get_stock_by_ticker(ticker.upper())
    if not stock:
        raise ValueError(f"Unknown ticker: {ticker}")
    return generate_features_for_stock(stock["id"], repository=repository)


def generate_features_for_universe(
    universe_slug: str,
    *,
    repository: SupabaseRepository | None = None,
    max_tickers: int | None = None,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    members = list_universe_members(universe_slug, repository=repository)
    if max_tickers is not None:
        members = members[: max(0, max_tickers)]
    results: list[dict[str, Any]] = []
    failures: list[str] = []

    for member in members:
        stock = member.get("stocks") or {}
        stock_id = stock.get("id")
        ticker = stock.get("ticker")
        if not stock_id:
            continue
        try:
            outcome = generate_features_for_stock(stock_id, repository=repository)
            results.append({"ticker": ticker, **outcome})
        except Exception as exc:
            failures.append(f"{ticker}: {exc}")

    return {
        "universe": universe_slug,
        "processed": len(results),
        "failed": len(failures),
        "results": results,
        "failures": failures,
    }
