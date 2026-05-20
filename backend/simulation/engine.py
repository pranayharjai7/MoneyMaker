from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from statistics import fmean, pstdev
from typing import Any

import math

from backend.core.math_utils import clamp, safe_float
from backend.db.repository import SupabaseRepository


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


def _partial_fill_ratio(signal: Mapping[str, Any]) -> float:
    risk_score = clamp(safe_float(signal.get("risk_score"), 0.5))
    probability = max(
        safe_float(signal.get("buy_probability"), 0.5),
        safe_float(signal.get("sell_probability"), 0.5),
    )
    return clamp((1.0 - risk_score * 0.45) * (0.75 + probability * 0.25), 0.45, 1.0)


def _max_drawdown(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_drawdown = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = min(max_drawdown, (equity / peak) - 1.0)
    return max_drawdown


def _streaks(returns: list[float]) -> tuple[int, int]:
    max_win = max_loss = current_win = current_loss = 0
    for value in returns:
        if value > 0:
            current_win += 1
            current_loss = 0
        elif value < 0:
            current_loss += 1
            current_win = 0
        else:
            current_win = current_loss = 0
        max_win = max(max_win, current_win)
        max_loss = max(max_loss, current_loss)
    return max_win, max_loss


def _sharpe_ratio(trade_returns: list[float], hold_days: list[int]) -> float:
    if len(trade_returns) < 2:
        return 0.0
    volatility = pstdev(trade_returns)
    if volatility <= 0:
        return 0.0
    annualizer = math.sqrt(252.0 / max(fmean(hold_days), 1.0))
    return safe_float((fmean(trade_returns) / volatility) * annualizer)


def _simulate_trade(
    repository: SupabaseRepository,
    signal: Mapping[str, Any],
    execution_delay_days: int,
    slippage_bps: float,
    transaction_cost_bps: float,
    max_trade_allocation: float,
) -> dict[str, Any] | None:
    signal_type = str(signal.get("signal_type") or "neutral")
    if signal_type not in {"buy", "sell"}:
        return None

    stock_id = str(signal.get("stock_id") or "")
    signal_time = _to_utc_datetime(signal["timestamp"])
    hold_days = max(1, int(signal.get("suggested_hold_days") or 1))
    entry_time = signal_time + timedelta(days=execution_delay_days)
    exit_time = entry_time + timedelta(days=hold_days)
    entry_price = repository.get_price_at_or_after(stock_id, _iso(entry_time))
    exit_price = repository.get_price_at_or_after(stock_id, _iso(exit_time))
    entry_close = _close(entry_price)
    exit_close = _close(exit_price)
    if entry_close <= 0 or exit_close <= 0:
        return None

    direction = 1.0 if signal_type == "buy" else -1.0
    gross_return = direction * ((exit_close - entry_close) / entry_close)
    slippage_cost = slippage_bps / 10000.0 * 2.0
    transaction_cost = transaction_cost_bps / 10000.0 * 2.0
    fill_ratio = _partial_fill_ratio(signal)
    conviction = abs(
        safe_float(signal.get("buy_probability"), 0.5) - safe_float(signal.get("sell_probability"), 0.5)
    )
    allocation = min(max_trade_allocation, max_trade_allocation * conviction * fill_ratio)
    net_return = gross_return - slippage_cost - transaction_cost
    contribution = allocation * net_return
    return {
        "stock_id": stock_id,
        "signal_timestamp": _iso(signal_time),
        "entry_timestamp": str((entry_price or {}).get("timestamp")),
        "exit_timestamp": str((exit_price or {}).get("timestamp")),
        "direction": signal_type,
        "hold_days": hold_days,
        "fill_ratio": fill_ratio,
        "allocation": allocation,
        "gross_return": gross_return,
        "net_return": net_return,
        "contribution": contribution,
        "transaction_cost": allocation * transaction_cost,
        "slippage_cost": allocation * slippage_cost,
    }


def run_paper_trading_simulation(
    repository: SupabaseRepository | None = None,
    signal_limit: int = 1000,
    execution_delay_days: int = 1,
    slippage_bps: float = 5.0,
    transaction_cost_bps: float = 2.0,
    max_trade_allocation: float = 0.10,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    signals = repository.list_signals_for_backtest(limit=signal_limit)
    trades = [
        trade
        for signal in signals
        if (
            trade := _simulate_trade(
                repository=repository,
                signal=signal,
                execution_delay_days=execution_delay_days,
                slippage_bps=slippage_bps,
                transaction_cost_bps=transaction_cost_bps,
                max_trade_allocation=max_trade_allocation,
            )
        )
    ]

    equity = 1.0
    equity_curve = [equity]
    trade_returns = []
    hold_days = []
    for trade in trades:
        contribution = safe_float(trade.get("contribution"))
        equity *= 1.0 + contribution
        equity_curve.append(equity)
        trade_returns.append(contribution)
        hold_days.append(max(1, int(trade.get("hold_days") or 1)))

    wins = sum(1 for value in trade_returns if value > 0)
    max_win_streak, max_loss_streak = _streaks(trade_returns)
    result = {
        "strategy_return": equity - 1.0,
        "max_drawdown": _max_drawdown(equity_curve),
        "sharpe_ratio": _sharpe_ratio(trade_returns, hold_days),
        "trade_count": len(trades),
        "win_rate": clamp(wins / len(trades)) if trades else 0.0,
        "max_win_streak": max_win_streak,
        "max_loss_streak": max_loss_streak,
        "total_transaction_costs": sum(safe_float(trade.get("transaction_cost")) for trade in trades),
        "average_slippage_bps": slippage_bps,
        "parameters": {
            "signal_limit": signal_limit,
            "execution_delay_days": execution_delay_days,
            "slippage_bps": slippage_bps,
            "transaction_cost_bps": transaction_cost_bps,
            "max_trade_allocation": max_trade_allocation,
        },
        "result_payload": {
            "equity_curve": equity_curve,
            "trades": trades[-100:],
        },
    }
    return repository.insert_backtest_result(result) or result
