from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Literal

from backend.core.config import Settings, get_settings
from backend.data_pipeline.providers import PriceBar
from backend.db.repository import SupabaseRepository
from backend.historical_backfill.chunks import (
    ChunkGranularity,
    chunk_is_fully_covered,
    compute_backfill_window,
    iter_date_chunks,
)
from backend.historical_backfill.fetcher import ProviderFetchError, fetch_prices_with_failover
from backend.historical_universe.service import list_universe_members, sync_universe

Resolution = Literal["daily", "hourly"]


@dataclass(frozen=True)
class BackfillResult:
    ticker: str
    stock_id: str
    chunks_total: int
    chunks_fetched: int
    chunks_skipped: int
    bars_stored: int
    provider: str | None
    status: str


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value)
    if "T" in text:
        text = text.split("T", 1)[0]
    return date.fromisoformat(text)


def _bar_dates(bars: list[PriceBar]) -> tuple[date | None, date | None]:
    if not bars:
        return None, None
    days = sorted(bar.timestamp.date() for bar in bars)
    return days[0], days[-1]


async def backfill_ticker(
    ticker: str,
    *,
    years: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    resolution: Resolution = "daily",
    chunk_granularity: ChunkGranularity | None = None,
    repository: SupabaseRepository | None = None,
    settings: Settings | None = None,
) -> BackfillResult:
    """Backfill real historical OHLCV for one ticker with chunked incremental ingestion."""
    if resolution == "hourly":
        raise NotImplementedError("Hourly backfill is reserved for a later phase; use resolution='daily'.")

    settings = settings or get_settings()
    repository = repository or SupabaseRepository()
    years = years if years is not None else settings.historical_backfill_years
    granularity: ChunkGranularity = chunk_granularity or settings.historical_backfill_chunk_granularity_normalized  # type: ignore[assignment]

    stock = repository.get_stock_by_ticker(ticker.upper())
    if not stock:
        upserted = repository.upsert_stocks(
            [{"ticker": ticker.upper(), "company_name": ticker.upper(), "exchange": "US"}]
        )
        stock = upserted[0] if upserted else repository.get_stock_by_ticker(ticker.upper())
    if not stock:
        raise ValueError(f"Unable to resolve stock row for {ticker}")

    target_start, target_end = (
        (start_date, end_date)
        if start_date and end_date
        else compute_backfill_window(years=years, end_date=end_date)
    )
    if start_date and not end_date:
        target_end = date.today()
    if end_date and not start_date:
        target_start, _ = compute_backfill_window(years=years, end_date=end_date)

    chunks = iter_date_chunks(target_start, target_end, granularity=granularity)
    state = repository.get_price_backfill_state(stock["id"], resolution=resolution)
    last_through = _parse_date(state.get("last_backfilled_through")) if state else None

    repository.upsert_price_backfill_state(
        stock_id=stock["id"],
        resolution=resolution,
        target_start_date=target_start.isoformat(),
        target_end_date=target_end.isoformat(),
        status="in_progress",
        chunks_total=len(chunks),
        chunks_completed=int(state.get("chunks_completed") or 0) if state else 0,
        last_backfilled_through=last_through.isoformat() if last_through else None,
    )

    chunks_fetched = 0
    chunks_skipped = 0
    bars_stored_total = int(state.get("bars_stored") or 0) if state else 0
    last_provider: str | None = state.get("last_provider") if state else None
    earliest = _parse_date(state.get("earliest_stored_date")) if state else None
    latest = _parse_date(state.get("latest_stored_date")) if state else None
    last_error: str | None = None

    try:
        for chunk_start, chunk_end in chunks:
            if chunk_is_fully_covered(chunk_start, chunk_end, last_through):
                chunks_skipped += 1
                continue

            bars, provider = await fetch_prices_with_failover(
                stock["ticker"],
                chunk_start,
                chunk_end,
                settings=settings,
                provider_cooldown_seconds=settings.historical_backfill_provider_cooldown_seconds,
            )
            if not bars:
                chunks_skipped += 1
                continue

            stored = repository.upsert_prices([bar.to_row(stock["id"]) for bar in bars])
            chunks_fetched += 1
            bars_stored_total += len(stored)
            last_provider = provider
            last_through = chunk_end

            chunk_earliest, chunk_latest = _bar_dates(bars)
            if chunk_earliest:
                earliest = min(filter(None, [earliest, chunk_earliest]))
            if chunk_latest:
                latest = max(filter(None, [latest, chunk_latest]))

            repository.upsert_price_backfill_state(
                stock_id=stock["id"],
                resolution=resolution,
                target_start_date=target_start.isoformat(),
                target_end_date=target_end.isoformat(),
                status="in_progress",
                earliest_stored_date=earliest.isoformat() if earliest else None,
                latest_stored_date=latest.isoformat() if latest else None,
                last_backfilled_through=last_through.isoformat(),
                last_provider=last_provider,
                bars_stored=bars_stored_total,
                chunks_total=len(chunks),
                chunks_completed=chunks_fetched + chunks_skipped,
            )

        final_status = "completed" if (chunks_fetched + chunks_skipped) >= len(chunks) else "failed"
        repository.upsert_price_backfill_state(
            stock_id=stock["id"],
            resolution=resolution,
            target_start_date=target_start.isoformat(),
            target_end_date=target_end.isoformat(),
            status=final_status,
            earliest_stored_date=earliest.isoformat() if earliest else None,
            latest_stored_date=latest.isoformat() if latest else None,
            last_backfilled_through=last_through.isoformat() if last_through else None,
            last_provider=last_provider,
            bars_stored=bars_stored_total,
            chunks_total=len(chunks),
            chunks_completed=chunks_fetched + chunks_skipped,
        )
        return BackfillResult(
            ticker=stock["ticker"],
            stock_id=stock["id"],
            chunks_total=len(chunks),
            chunks_fetched=chunks_fetched,
            chunks_skipped=chunks_skipped,
            bars_stored=bars_stored_total,
            provider=last_provider,
            status=final_status,
        )
    except (ProviderFetchError, Exception) as exc:
        last_error = str(exc)
        repository.upsert_price_backfill_state(
            stock_id=stock["id"],
            resolution=resolution,
            target_start_date=target_start.isoformat(),
            target_end_date=target_end.isoformat(),
            status="failed",
            earliest_stored_date=earliest.isoformat() if earliest else None,
            latest_stored_date=latest.isoformat() if latest else None,
            last_backfilled_through=last_through.isoformat() if last_through else None,
            last_provider=last_provider,
            bars_stored=bars_stored_total,
            chunks_total=len(chunks),
            chunks_completed=chunks_fetched + chunks_skipped,
            last_error=last_error,
        )
        raise


async def backfill_universe(
    universe_slug: str,
    *,
    years: int | None = None,
    resolution: Resolution = "daily",
    sync_members: bool = True,
    repository: SupabaseRepository | None = None,
    settings: Settings | None = None,
    max_tickers: int | None = None,
) -> dict[str, Any]:
    """Backfill all members of a configured universe."""
    repository = repository or SupabaseRepository()
    if sync_members:
        sync_universe(universe_slug, repository=repository)

    members = list_universe_members(universe_slug, repository=repository)
    tickers = [
        str((member.get("stocks") or {}).get("ticker", "")).upper()
        for member in members
        if (member.get("stocks") or {}).get("ticker")
    ]
    if max_tickers is not None:
        tickers = tickers[: max(0, max_tickers)]

    results: list[dict[str, Any]] = []
    failures: list[str] = []
    for ticker in tickers:
        try:
            outcome = await backfill_ticker(
                ticker,
                years=years,
                resolution=resolution,
                repository=repository,
                settings=settings,
            )
            results.append(
                {
                    "ticker": outcome.ticker,
                    "status": outcome.status,
                    "bars_stored": outcome.bars_stored,
                    "chunks_fetched": outcome.chunks_fetched,
                    "chunks_skipped": outcome.chunks_skipped,
                }
            )
        except Exception as exc:
            failures.append(f"{ticker}: {exc}")

    return {
        "universe": universe_slug,
        "tickers_processed": len(results),
        "tickers_failed": len(failures),
        "results": results,
        "failures": failures,
    }
