from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from backend.core.math_utils import safe_float
from backend.historical_replay.context import StockSeries, _to_utc_datetime


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def evaluate_signal_outcome(
    signal: dict[str, Any],
    series: StockSeries,
    *,
    execution_delay_days: int = 1,
) -> dict[str, Any] | None:
    """Simulate trade outcome using real prices after the signal (labels only, not features)."""
    signal_type = str(signal.get("signal_type") or "neutral")
    if signal_type not in {"buy", "sell"}:
        return None

    signal_time = _to_utc_datetime(signal["timestamp"])
    hold_days = max(1, int(signal.get("hold_days") or 5))
    entry_time = signal_time + timedelta(days=execution_delay_days)
    exit_time = entry_time + timedelta(days=hold_days)

    entry_row = series.price_at_or_after(entry_time)
    exit_row = series.price_at_or_after(exit_time)
    if not entry_row or not exit_row:
        return None

    entry_price = safe_float(entry_row.get("close"))
    exit_price = safe_float(exit_row.get("close"))
    if entry_price <= 0 or exit_price <= 0:
        return None

    raw_return = (exit_price / entry_price) - 1.0
    actual_return = raw_return if signal_type == "buy" else -raw_return
    if actual_return > 0.001:
        outcome = "win"
    elif actual_return < -0.001:
        outcome = "loss"
    else:
        outcome = "flat"

    return {
        "stock_id": signal["stock_id"],
        "entry_timestamp": _iso(_to_utc_datetime(entry_row["timestamp"])),
        "exit_timestamp": _iso(_to_utc_datetime(exit_row["timestamp"])),
        "entry_price": entry_price,
        "exit_price": exit_price,
        "actual_return": actual_return,
        "horizon_days": hold_days,
        "outcome": outcome,
        "pnl": actual_return,
    }
