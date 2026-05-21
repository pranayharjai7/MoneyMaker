from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from statistics import fmean
from typing import Any

from backend.core.math_utils import clamp, safe_float
from backend.db.repository import SupabaseRepository
from backend.simulation.engine import run_paper_trading_simulation


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


def _date_key(value: Any) -> str:
    return _to_utc_datetime(value).date().isoformat()


def _payload(result: Mapping[str, Any]) -> dict[str, Any]:
    payload = result.get("result_payload") or {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _trades(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    trades = _payload(result).get("trades") or []
    return [dict(row) for row in trades if isinstance(row, Mapping)]


def _equity_curve(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    values = _payload(result).get("equity_curve") or []
    if not isinstance(values, Sequence):
        return []
    trades = _trades(result)
    curve = []
    for index, equity in enumerate(values):
        timestamp = None
        if index > 0 and index - 1 < len(trades):
            timestamp = trades[index - 1].get("exit_timestamp")
        curve.append(
            {
                "index": index,
                "timestamp": timestamp,
                "equity": safe_float(equity, 1.0),
                "cumulative_return": safe_float(equity, 1.0) - 1.0,
            }
        )
    return curve


def _daily_pnl(trades: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, float] = defaultdict(float)
    for trade in trades:
        timestamp = trade.get("exit_timestamp") or trade.get("entry_timestamp")
        if not timestamp:
            continue
        grouped[_date_key(timestamp)] += safe_float(trade.get("contribution"))
    return [
        {"date": date, "pnl": pnl}
        for date, pnl in sorted(grouped.items(), key=lambda item: item[0])
    ]


def _regime_adjusted_returns(
    repository: SupabaseRepository,
    trades: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for trade in trades:
        timestamp = trade.get("entry_timestamp") or trade.get("signal_timestamp")
        if not timestamp:
            continue
        regime = repository.get_market_regime_at_or_before(str(timestamp)) or {}
        regime_name = str(regime.get("current_regime") or "UNKNOWN")
        grouped[regime_name].append(safe_float(trade.get("contribution")))
    rows = []
    for regime, values in sorted(grouped.items()):
        wins = sum(1 for value in values if value > 0)
        rows.append(
            {
                "regime": regime,
                "trade_count": len(values),
                "average_return": fmean(values) if values else 0.0,
                "cumulative_return": sum(values),
                "win_rate": clamp(wins / len(values)) if values else 0.0,
            }
        )
    return rows


def latest_or_run_paper_result(
    repository: SupabaseRepository | None = None,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    return repository.latest_backtest_result() or run_paper_trading_simulation(repository=repository)


def build_paper_performance_report(
    repository: SupabaseRepository | None = None,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    result = latest_or_run_paper_result(repository)
    trades = _trades(result)
    return {
        "portfolio_return": safe_float(result.get("strategy_return")),
        "sharpe_ratio": safe_float(result.get("sharpe_ratio")),
        "max_drawdown": safe_float(result.get("max_drawdown")),
        "win_rate": clamp(safe_float(result.get("win_rate"))),
        "trade_count": int(result.get("trade_count") or len(trades)),
        "daily_pnl": _daily_pnl(trades),
        "equity_curve": _equity_curve(result),
        "trade_history": trades,
        "regime_adjusted_returns": _regime_adjusted_returns(repository, trades),
        "source_result": result,
    }


def paper_history(repository: SupabaseRepository | None = None) -> list[dict[str, Any]]:
    return build_paper_performance_report(repository)["trade_history"]


def paper_equity_curve(repository: SupabaseRepository | None = None) -> list[dict[str, Any]]:
    return build_paper_performance_report(repository)["equity_curve"]


def paper_regime_adjusted_returns(repository: SupabaseRepository | None = None) -> list[dict[str, Any]]:
    return build_paper_performance_report(repository)["regime_adjusted_returns"]
