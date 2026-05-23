from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Literal

import pandas as pd

from backend.core.math_utils import clamp, safe_float
from backend.db.repository import SupabaseRepository
from backend.historical_replay.context import ReplayDataset, _day_start
from backend.historical_replay.outcomes import evaluate_signal_outcome
from backend.historical_replay.portfolio import PaperPortfolio
from backend.historical_replay.regime import detect_regime_at
from backend.historical_replay.signals import generate_point_in_time_signal
from backend.historical_universe.service import list_universe_members

ReplayMode = Literal["signal_only", "paper_portfolio", "adaptive"]
UTC = timezone.utc


@dataclass(frozen=True)
class ReplayConfig:
    universe_name: str
    mode: ReplayMode = "signal_only"
    start_date: date | None = None
    end_date: date | None = None
    years: int = 2
    max_stocks: int | None = 25
    checkpoint_every_days: int = 5
    meta_model_version: str = "replay_v1"
    initial_cash: float = 100_000.0


def _resolve_window(config: ReplayConfig) -> tuple[date, date]:
    end = config.end_date or date.today()
    start = config.start_date or (end - timedelta(days=max(config.years, 1) * 365))
    return start, end


def _latest_timestamp_iso(prices: pd.DataFrame) -> str:
    timestamp = pd.to_datetime(prices.iloc[-1]["timestamp"], utc=True)
    return timestamp.isoformat()


def _adaptive_performances(history: dict[str, list[float]]) -> dict[str, dict[str, Any]]:
    performances: dict[str, dict[str, Any]] = {}
    for model_name, returns in history.items():
        if not returns:
            continue
        wins = sum(1 for value in returns if value > 0)
        performances[model_name] = {
            "accuracy": wins / len(returns),
            "brier_score": 0.2,
            "calibration_error": 0.15,
            "sharpe_contribution": 0.0,
        }
    return performances


def _update_adaptive_history(
    history: dict[str, list[float]],
    model_predictions: list[dict[str, Any]],
    actual_return: float,
) -> None:
    for prediction in model_predictions:
        model_name = str(prediction.get("model_name"))
        probability = clamp(safe_float(prediction.get("probability_up"), 0.5))
        signed = actual_return if probability >= 0.5 else -actual_return
        history[model_name].append(signed)


def _persist_day(
    *,
    repository: SupabaseRepository,
    replay_run_id: str,
    pending_signals: list[tuple[dict[str, Any], Any]],
    config: ReplayConfig,
    adaptive_history: dict[str, list[float]],
    outcomes_evaluated: int,
) -> int:
    if not pending_signals:
        return outcomes_evaluated

    signal_rows = [signal for signal, _ in pending_signals]
    stored_signals = repository.insert_historical_signals(signal_rows)
    for stored, (original, series) in zip(stored_signals, pending_signals, strict=False):
        signal_id = stored.get("id")
        if not signal_id:
            continue
        outcome = evaluate_signal_outcome(original, series)
        if not outcome:
            continue
        repository.insert_replay_outcome(
            replay_run_id=replay_run_id,
            historical_signal_id=str(signal_id),
            **outcome,
        )
        outcomes_evaluated += 1
        if config.mode == "adaptive":
            _update_adaptive_history(
                adaptive_history,
                original.get("model_predictions") or [],
                safe_float(outcome.get("actual_return")),
            )
    return outcomes_evaluated


def run_replay(
    replay_run_id: str,
    *,
    repository: SupabaseRepository | None = None,
    config: ReplayConfig | None = None,
    resume: bool = True,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    run = repository.get_replay_run(replay_run_id)
    if not run:
        raise ValueError(f"Unknown replay run: {replay_run_id}")

    stored_config = dict(run.get("config") or {})
    config = config or ReplayConfig(
        universe_name=str(run.get("universe_name") or stored_config.get("universe_name") or "high_liquidity"),
        mode=str(run.get("mode") or stored_config.get("mode") or "signal_only"),  # type: ignore[arg-type]
        start_date=date.fromisoformat(str(run["start_date"])),
        end_date=date.fromisoformat(str(run["end_date"])),
        years=int(stored_config.get("years") or 2),
        max_stocks=stored_config.get("max_stocks"),
        checkpoint_every_days=int(stored_config.get("checkpoint_every_days") or 5),
        meta_model_version=str(run.get("meta_model_version") or "replay_v1"),
        initial_cash=float(stored_config.get("initial_cash") or 100_000.0),
    )

    members = list_universe_members(config.universe_name, repository=repository)
    stock_ids: list[str] = []
    tickers_by_id: dict[str, str] = {}
    for member in members:
        stock = member.get("stocks") or {}
        stock_id = stock.get("id")
        ticker = stock.get("ticker")
        if not stock_id or not ticker:
            continue
        stock_ids.append(str(stock_id))
        tickers_by_id[str(stock_id)] = str(ticker).upper()
    if config.max_stocks is not None:
        stock_ids = stock_ids[: max(0, config.max_stocks)]

    start_date, end_date = _resolve_window(config)
    dataset = ReplayDataset.load(
        repository,
        stock_ids=stock_ids,
        tickers_by_id=tickers_by_id,
        start_date=start_date,
        end_date=end_date,
    )
    if not dataset.trading_days:
        repository.update_replay_run(
            replay_run_id,
            status="failed",
            last_error="No trading days found. Backfill SPY (or benchmark) prices first.",
        )
        return {"status": "failed", "reason": "no_trading_days"}

    resume_from: date | None = None
    if resume and run.get("last_replay_date"):
        resume_from = date.fromisoformat(str(run["last_replay_date"]))

    repository.update_replay_run(replay_run_id, status="running")
    portfolio = PaperPortfolio(cash=config.initial_cash)
    adaptive_history: dict[str, list[float]] = defaultdict(list)
    signals_generated = int(run.get("signals_generated") or 0)
    outcomes_evaluated = int(run.get("outcomes_evaluated") or 0)
    days_processed = 0

    try:
        for index, trading_day in enumerate(dataset.trading_days):
            if resume_from and trading_day <= resume_from:
                continue

            as_of = datetime.combine(trading_day, time.min, tzinfo=UTC)
            regime = detect_regime_at(dataset.benchmark_slice_before(as_of))
            model_performances = (
                _adaptive_performances(adaptive_history) if config.mode == "adaptive" else {}
            )
            pending_signals: list[tuple[dict[str, Any], Any]] = []
            marks: dict[str, float] = {}

            for stock_id, series in dataset.stocks.items():
                prices, features = series.slice_before(as_of)
                if len(prices) < 60 or len(features) < 60:
                    continue

                signal = generate_point_in_time_signal(
                    stock_id=stock_id,
                    prices=prices,
                    features=features,
                    regime=regime,
                    signal_timestamp=_latest_timestamp_iso(prices),
                    meta_model_version=config.meta_model_version,
                    model_performances=model_performances,
                )
                if not signal:
                    continue

                signal["replay_run_id"] = replay_run_id
                pending_signals.append((signal, series))
                signals_generated += 1
                marks[stock_id] = safe_float(prices.iloc[-1]["close"])

                if config.mode in {"paper_portfolio", "adaptive"}:
                    portfolio.process_signal(signal, marks=marks)

            outcomes_evaluated = _persist_day(
                repository=repository,
                replay_run_id=replay_run_id,
                pending_signals=pending_signals,
                config=config,
                adaptive_history=adaptive_history,
                outcomes_evaluated=outcomes_evaluated,
            )

            if config.mode in {"paper_portfolio", "adaptive"}:
                repository.insert_replay_portfolio_snapshot(
                    replay_run_id=replay_run_id,
                    **portfolio.snapshot(trading_day, marks),
                )

            days_processed += 1
            if days_processed % max(1, config.checkpoint_every_days) == 0 or index == len(dataset.trading_days) - 1:
                repository.update_replay_run(
                    replay_run_id,
                    status="running",
                    last_replay_date=trading_day.isoformat(),
                    signals_generated=signals_generated,
                    outcomes_evaluated=outcomes_evaluated,
                )

        repository.update_replay_run(
            replay_run_id,
            status="completed",
            last_replay_date=end_date.isoformat(),
            signals_generated=signals_generated,
            outcomes_evaluated=outcomes_evaluated,
        )
        return {
            "status": "completed",
            "signals_generated": signals_generated,
            "outcomes_evaluated": outcomes_evaluated,
            "days_processed": days_processed,
        }
    except Exception as exc:
        repository.update_replay_run(
            replay_run_id,
            status="failed",
            last_error=str(exc),
            signals_generated=signals_generated,
            outcomes_evaluated=outcomes_evaluated,
        )
        raise
