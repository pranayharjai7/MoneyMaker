from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from statistics import fmean, pstdev
from typing import Any

import math

from backend.core.math_utils import clamp, safe_float
from backend.db.repository import SupabaseRepository


DEFAULT_SIGNAL_HORIZON_DAYS = 5
QUALITY_WINDOW_LIMIT = 1000


def _to_utc_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value)
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _close(row: Mapping[str, Any] | None) -> float:
    return safe_float((row or {}).get("close"))


def _direction(signal: Mapping[str, Any]) -> str:
    signal_type = str(signal.get("signal_type") or "neutral").lower()
    if signal_type in {"buy", "sell"}:
        return signal_type
    buy_probability = safe_float(signal.get("buy_probability"), 0.5)
    sell_probability = safe_float(signal.get("sell_probability"), 0.5)
    if buy_probability > sell_probability and safe_float(signal.get("expected_return")) > 0:
        return "buy"
    if sell_probability > buy_probability and safe_float(signal.get("expected_return")) < 0:
        return "sell"
    return "neutral"


def _pnl(signal: Mapping[str, Any], actual_return: float) -> float:
    direction = _direction(signal)
    if direction == "sell":
        return -actual_return
    if direction == "buy":
        return actual_return
    return -abs(actual_return) * 0.05


def _outcome(pnl: float) -> str:
    if pnl > 0:
        return "win"
    if pnl < 0:
        return "loss"
    return "flat"


def _model_used(repository: SupabaseRepository, signal: Mapping[str, Any]) -> str:
    model_used = signal.get("model_used")
    if model_used:
        return str(model_used)
    latest_training_run = repository.latest_meta_model_training_run()
    if latest_training_run and latest_training_run.get("model_type"):
        return str(latest_training_run["model_type"])
    return "meta_model_ensemble"


def _regime_at(repository: SupabaseRepository, timestamp: str) -> str:
    regime = repository.get_market_regime_at_or_before(timestamp) or repository.latest_market_regime()
    return str((regime or {}).get("current_regime") or "UNKNOWN")


def _live_performance_row(
    repository: SupabaseRepository,
    signal: Mapping[str, Any],
    horizon_days: int,
) -> dict[str, Any] | None:
    signal_id = signal.get("id")
    stock_id = signal.get("stock_id")
    timestamp = signal.get("timestamp")
    if not signal_id or not stock_id or not timestamp:
        return None

    signal_time = _to_utc_datetime(timestamp)
    entry_price = repository.get_price_at_or_before(str(stock_id), _iso(signal_time))
    exit_time = signal_time + timedelta(days=horizon_days)
    exit_price = repository.get_price_at_or_after(str(stock_id), _iso(exit_time))
    entry_close = _close(entry_price)
    exit_close = _close(exit_price)
    if entry_close <= 0 or exit_close <= 0:
        return None

    actual_return = (exit_close - entry_close) / entry_close
    pnl = _pnl(signal, actual_return)
    return {
        "signal_id": str(signal_id),
        "stock_id": str(stock_id),
        "model_used": _model_used(repository, signal),
        "regime": _regime_at(repository, _iso(signal_time)),
        "predicted_return": safe_float(signal.get("expected_return")),
        "actual_return": actual_return,
        "horizon_days": horizon_days,
        "outcome": _outcome(pnl),
        "pnl": pnl,
    }


def _max_drawdown(returns: Sequence[float]) -> float:
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for value in returns:
        equity *= 1.0 + value
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = min(max_drawdown, (equity / peak) - 1.0)
    return max_drawdown


def _sharpe_ratio(returns: Sequence[float], horizon_days: int) -> float:
    if len(returns) < 2:
        return 0.0
    volatility = pstdev(returns)
    if volatility <= 0:
        return 0.0
    annualizer = math.sqrt(252.0 / max(horizon_days, 1))
    return safe_float((fmean(returns) / volatility) * annualizer)


def _profit_factor(returns: Sequence[float]) -> float:
    gains = sum(value for value in returns if value > 0)
    losses = abs(sum(value for value in returns if value < 0))
    if losses <= 0:
        return gains if gains > 0 else 0.0
    return gains / losses


def _regime_performance_rows(
    rows: Iterable[Mapping[str, Any]],
    updated_at: datetime,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        model_name = row.get("model_used") or row.get("model_name")
        regime = row.get("regime")
        if model_name and regime:
            grouped[(str(model_name), str(regime))].append(row)

    result = []
    for (model_name, regime), group in grouped.items():
        pnl_values = [safe_float(row.get("pnl")) for row in group]
        wins = sum(1 for value in pnl_values if value > 0)
        horizon = max(1, int(group[0].get("horizon_days") or DEFAULT_SIGNAL_HORIZON_DAYS))
        result.append(
            {
                "model_name": model_name,
                "regime": regime,
                "win_rate": clamp(wins / len(group)) if group else 0.0,
                "sharpe_ratio": _sharpe_ratio(pnl_values, horizon_days=horizon),
                "average_return": fmean(pnl_values) if pnl_values else 0.0,
                "sample_size": len(group),
                "profit_factor": _profit_factor(pnl_values),
                "max_drawdown": _max_drawdown(pnl_values),
                "updated_at": _iso(updated_at),
            }
        )
    return result


def evaluate_live_signal_quality(
    repository: SupabaseRepository | None = None,
    horizon_days: int = DEFAULT_SIGNAL_HORIZON_DAYS,
    signal_limit: int = QUALITY_WINDOW_LIMIT,
    as_of: datetime | None = None,
) -> dict[str, int]:
    """Evaluate matured live ensemble signals against realized prices."""

    repository = repository or SupabaseRepository()
    as_of = (as_of or datetime.now(tz=UTC)).astimezone(UTC)
    horizon_days = max(1, int(horizon_days))
    cutoff = as_of - timedelta(days=horizon_days)
    signals = repository.list_signals_for_quality(_iso(cutoff), limit=signal_limit)
    rows = [
        row
        for signal in signals
        if (row := _live_performance_row(repository, signal, horizon_days))
    ]
    stored_rows = repository.upsert_live_signal_performance(rows)
    performance_source = repository.list_live_signal_performance(limit=signal_limit)
    if not performance_source:
        performance_source = stored_rows
    regime_rows = _regime_performance_rows(performance_source, updated_at=as_of)
    stored_regimes = repository.upsert_model_regime_performance(regime_rows)
    return {
        "evaluated_signals": len(signals),
        "live_signal_performance": len(stored_rows),
        "model_regime_performance": len(stored_regimes),
    }


def best_models_by_regime(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("regime") and row.get("model_name"):
            grouped[str(row["regime"])].append(row)

    best: dict[str, dict[str, Any]] = {}
    for regime, regime_rows in grouped.items():
        ranked = sorted(
            regime_rows,
            key=lambda row: (
                safe_float(row.get("sharpe_ratio")),
                safe_float(row.get("win_rate")),
                safe_float(row.get("profit_factor")),
            ),
            reverse=True,
        )
        if ranked:
            best[regime] = dict(ranked[0])
    return best


def build_signal_quality_report(
    repository: SupabaseRepository | None = None,
    limit: int = QUALITY_WINDOW_LIMIT,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    live_rows = repository.list_live_signal_performance(limit=limit)
    regime_rows = repository.list_model_regime_performance()
    pnl_values = [safe_float(row.get("pnl")) for row in live_rows]
    wins = sum(1 for value in pnl_values if value > 0)
    return {
        "summary": {
            "sample_size": len(live_rows),
            "win_rate": clamp(wins / len(live_rows)) if live_rows else 0.0,
            "average_pnl": fmean(pnl_values) if pnl_values else 0.0,
            "sharpe_ratio": _sharpe_ratio(pnl_values, horizon_days=DEFAULT_SIGNAL_HORIZON_DAYS),
            "max_drawdown": _max_drawdown(pnl_values),
            "profit_factor": _profit_factor(pnl_values),
        },
        "best_models_by_regime": best_models_by_regime(regime_rows),
        "model_regime_performance": regime_rows,
        "recent_signals": live_rows[:100],
    }
