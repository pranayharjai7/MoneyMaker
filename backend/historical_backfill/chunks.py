from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Literal

ChunkGranularity = Literal["year", "month"]


def iter_date_chunks(
    start_date: date,
    end_date: date,
    *,
    granularity: ChunkGranularity = "year",
) -> list[tuple[date, date]]:
    """Split [start_date, end_date] into non-overlapping chunks for API-friendly fetches."""
    if start_date > end_date:
        return []
    if granularity == "year":
        return _year_chunks(start_date, end_date)
    return _month_chunks(start_date, end_date)


def _year_chunks(start_date: date, end_date: date) -> list[tuple[date, date]]:
    chunks: list[tuple[date, date]] = []
    year = start_date.year
    while year <= end_date.year:
        chunk_start = max(start_date, date(year, 1, 1))
        chunk_end = min(end_date, date(year, 12, 31))
        chunks.append((chunk_start, chunk_end))
        year += 1
    return chunks


def _month_chunks(start_date: date, end_date: date) -> list[tuple[date, date]]:
    chunks: list[tuple[date, date]] = []
    current = date(start_date.year, start_date.month, 1)
    while current <= end_date:
        last_day = calendar.monthrange(current.year, current.month)[1]
        month_end = date(current.year, current.month, last_day)
        chunk_start = max(start_date, current)
        chunk_end = min(end_date, month_end)
        chunks.append((chunk_start, chunk_end))
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return chunks


def chunk_is_fully_covered(
    chunk_start: date,
    chunk_end: date,
    last_backfilled_through: date | None,
) -> bool:
    """Return True when this chunk was already ingested in a prior run."""
    if last_backfilled_through is None:
        return False
    return last_backfilled_through >= chunk_end


def compute_backfill_window(
    *,
    years: int,
    end_date: date | None = None,
) -> tuple[date, date]:
    end = end_date or date.today()
    start = end - timedelta(days=max(years, 1) * 365)
    return start, end
