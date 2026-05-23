from __future__ import annotations

import math
from statistics import fmean, pstdev
from typing import Any

from backend.core.math_utils import safe_float
from backend.db.repository import SupabaseRepository


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


def _sharpe_ratio(returns: list[float]) -> float:
    if len(returns) < 2:
        return 0.0
    volatility = pstdev(returns)
    if volatility <= 0:
        return 0.0
    return safe_float((fmean(returns) / volatility) * math.sqrt(252.0))


def equity_curve_from_snapshots(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(snapshots, key=lambda row: str(row.get("snapshot_date")))
    curve = []
    for row in ordered:
        curve.append(
            {
                "date": row.get("snapshot_date"),
                "equity": safe_float(row.get("equity")),
                "cash": safe_float(row.get("cash")),
            }
        )
    return curve


def equity_curve_from_outcomes(outcomes: list[dict[str, Any]], initial_equity: float = 100_000.0) -> list[dict[str, Any]]:
    ordered = sorted(outcomes, key=lambda row: str(row.get("exit_timestamp")))
    equity = initial_equity
    curve = [{"date": None, "equity": equity}]
    for row in ordered:
        equity *= 1.0 + safe_float(row.get("actual_return")) * 0.05
        curve.append(
            {
                "date": row.get("exit_timestamp"),
                "equity": equity,
                "outcome": row.get("outcome"),
            }
        )
    return curve


def strategy_contribution_analysis(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[str, dict[str, float]] = {}
    for signal in signals:
        for prediction in signal.get("model_predictions") or []:
            model_name = str(prediction.get("model_name"))
            bucket = totals.setdefault(
                model_name,
                {"signals": 0.0, "probability_mass": 0.0, "expected_return_mass": 0.0},
            )
            bucket["signals"] += 1.0
            bucket["probability_mass"] += safe_float(prediction.get("probability_up"), 0.5)
            bucket["expected_return_mass"] += safe_float(prediction.get("expected_return"))
    rows = []
    for model_name, bucket in sorted(totals.items()):
        count = max(bucket["signals"], 1.0)
        rows.append(
            {
                "model_name": model_name,
                "signal_count": int(bucket["signals"]),
                "average_probability": bucket["probability_mass"] / count,
                "average_expected_return": bucket["expected_return_mass"] / count,
            }
        )
    return rows


def calibration_quality_timeline(
    snapshots: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    ordered = sorted(snapshots, key=lambda row: (str(row.get("as_of_date")), str(row.get("model_name"))))
    return [
        {
            "as_of_date": row.get("as_of_date"),
            "model_name": row.get("model_name"),
            "calibration_method": row.get("calibration_method"),
            "calibration_error": safe_float(row.get("calibration_error")),
            "sample_size": int(row.get("sample_size") or 0),
        }
        for row in ordered
    ]


def build_replay_performance_report(
    replay_run_id: str,
    *,
    repository: SupabaseRepository | None = None,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    run = repository.get_replay_run(replay_run_id)
    if not run:
        raise ValueError(f"Unknown replay run: {replay_run_id}")

    signals = repository.list_historical_signals(replay_run_id=replay_run_id, limit=50_000)
    outcomes = repository.list_replay_outcomes(replay_run_id=replay_run_id, limit=50_000)
    snapshots = repository.list_replay_portfolio_snapshots(replay_run_id=replay_run_id)
    calibration_snapshots = repository.list_historical_calibration_snapshots(replay_run_id=replay_run_id)

    trade_returns = [safe_float(row.get("actual_return")) for row in outcomes]
    wins = sum(1 for value in trade_returns if value > 0)
    equity_curve = (
        equity_curve_from_snapshots(snapshots)
        if snapshots
        else equity_curve_from_outcomes(outcomes)
    )
    equity_values = [safe_float(point.get("equity")) for point in equity_curve if point.get("equity")]

    cumulative_return = 0.0
    if len(equity_values) >= 2 and equity_values[0] > 0:
        cumulative_return = (equity_values[-1] / equity_values[0]) - 1.0

    return {
        "replay_run_id": replay_run_id,
        "universe_name": run.get("universe_name"),
        "mode": run.get("mode"),
        "status": run.get("status"),
        "signals_generated": int(run.get("signals_generated") or len(signals)),
        "outcomes_evaluated": int(run.get("outcomes_evaluated") or len(outcomes)),
        "cumulative_return": cumulative_return,
        "sharpe_ratio": _sharpe_ratio(trade_returns),
        "max_drawdown": _max_drawdown(equity_values),
        "win_rate": (wins / len(trade_returns)) if trade_returns else 0.0,
        "equity_curve": equity_curve,
        "calibration_timeline": calibration_quality_timeline(calibration_snapshots),
        "strategy_contribution": strategy_contribution_analysis(signals),
        "regime_breakdown": _regime_breakdown(signals, outcomes),
    }


def _regime_breakdown(
    signals: list[dict[str, Any]],
    outcomes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    outcomes_by_signal = {str(row["historical_signal_id"]): row for row in outcomes}
    buckets: dict[str, list[float]] = {}
    for signal in signals:
        signal_id = str(signal.get("id") or "")
        outcome = outcomes_by_signal.get(signal_id)
        if not outcome:
            continue
        regime = str(signal.get("regime") or "UNKNOWN")
        buckets.setdefault(regime, []).append(safe_float(outcome.get("actual_return")))
    rows = []
    for regime, returns in sorted(buckets.items()):
        rows.append(
            {
                "regime": regime,
                "trade_count": len(returns),
                "average_return": fmean(returns) if returns else 0.0,
                "win_rate": sum(1 for value in returns if value > 0) / len(returns) if returns else 0.0,
            }
        )
    return rows
