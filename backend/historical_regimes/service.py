from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timezone
from statistics import fmean, pstdev
from typing import Any

import math

from backend.core.math_utils import clamp, safe_float
from backend.db.repository import SupabaseRepository
from backend.historical_replay.context import _day_start
from backend.historical_replay.regime import detect_regime_at

UTC = timezone.utc


def _parse_date(value: Any) -> date:
    text = str(value)
    if "T" in text:
        text = text.split("T", 1)[0]
    return date.fromisoformat(text)


def detect_historical_regime_periods(
    *,
    repository: SupabaseRepository | None = None,
    replay_run_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    benchmark_ticker: str = "SPY",
) -> list[dict[str, Any]]:
    """Label contiguous regime periods from real benchmark OHLCV (no synthetic data)."""
    repository = repository or SupabaseRepository()
    stock = repository.get_stock_by_ticker(benchmark_ticker)
    if not stock:
        return []

    prices = repository.get_prices_in_range(
        stock["id"],
        start_timestamp=_day_start(start_date).isoformat() if start_date else None,
        end_timestamp=_day_start(end_date).isoformat() if end_date else None,
        limit=50_000,
    )
    if not prices:
        return []

    import pandas as pd

    frame = pd.DataFrame(prices)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    trading_days = sorted({ts.date() for ts in frame["timestamp"]})

    periods: list[dict[str, Any]] = []
    current_regime: str | None = None
    period_start: date | None = None
    period_confidence = 0.0
    period_volatility = 0.0
    period_closes: list[float] = []

    for trading_day in trading_days:
        as_of = datetime.combine(trading_day, time.min, tzinfo=UTC)
        benchmark_slice = frame[frame["timestamp"] < as_of]
        regime = detect_regime_at(benchmark_slice)
        label = str(regime.get("current_regime") or "SIDEWAYS")
        close = safe_float(benchmark_slice.iloc[-1]["close"]) if not benchmark_slice.empty else 0.0

        if current_regime is None:
            current_regime = label
            period_start = trading_day
            period_confidence = safe_float(regime.get("confidence"))
            period_volatility = safe_float(regime.get("volatility_proxy"))
            period_closes = [close] if close > 0 else []
            continue

        if label != current_regime and period_start is not None:
            periods.append(
                _period_row(
                    replay_run_id=replay_run_id,
                    regime=current_regime,
                    start_date=period_start,
                    end_date=trading_day,
                    confidence=period_confidence,
                    closes=period_closes,
                    volatility_proxy=period_volatility,
                )
            )
            current_regime = label
            period_start = trading_day
            period_confidence = safe_float(regime.get("confidence"))
            period_volatility = safe_float(regime.get("volatility_proxy"))
            period_closes = [close] if close > 0 else []
        elif close > 0:
            period_closes.append(close)

    if current_regime and period_start and trading_days:
        periods.append(
            _period_row(
                replay_run_id=replay_run_id,
                regime=current_regime,
                start_date=period_start,
                end_date=trading_days[-1],
                confidence=period_confidence,
                closes=period_closes,
                volatility_proxy=period_volatility,
            )
        )
    return periods


def _period_row(
    *,
    replay_run_id: str | None,
    regime: str,
    start_date: date,
    end_date: date,
    confidence: float,
    closes: list[float],
    volatility_proxy: float,
) -> dict[str, Any]:
    benchmark_return = 0.0
    if len(closes) >= 2 and closes[0] > 0:
        benchmark_return = (closes[-1] / closes[0]) - 1.0
    return {
        "replay_run_id": replay_run_id,
        "regime": regime,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "confidence": clamp(confidence),
        "benchmark_return": benchmark_return,
        "volatility_proxy": volatility_proxy,
    }


def persist_historical_regime_periods(
    periods: list[dict[str, Any]],
    *,
    repository: SupabaseRepository | None = None,
) -> list[dict[str, Any]]:
    repository = repository or SupabaseRepository()
    return repository.upsert_historical_regime_periods(periods)


def learn_strategy_performance_by_regime(
    replay_run_id: str,
    *,
    repository: SupabaseRepository | None = None,
) -> dict[str, Any]:
    """Aggregate replay outcomes by regime and model; upsert model_regime_performance."""
    repository = repository or SupabaseRepository()
    signals = repository.list_historical_signals(replay_run_id=replay_run_id, limit=50_000)
    outcomes = repository.list_replay_outcomes(replay_run_id=replay_run_id, limit=50_000)
    outcomes_by_signal = {str(row["historical_signal_id"]): row for row in outcomes}

    buckets: dict[tuple[str, str], list[float]] = defaultdict(list)
    for signal in signals:
        signal_id = str(signal.get("id") or "")
        outcome = outcomes_by_signal.get(signal_id)
        if not outcome:
            continue
        regime = str(signal.get("regime") or "SIDEWAYS")
        actual_return = safe_float(outcome.get("actual_return"))
        for prediction in signal.get("model_predictions") or []:
            model_name = str(prediction.get("model_name"))
            probability = clamp(safe_float(prediction.get("probability_up"), 0.5))
            signed = actual_return if probability >= 0.5 else -actual_return
            buckets[(model_name, regime)].append(signed)

    rows = []
    for (model_name, regime), returns in buckets.items():
        if not returns:
            continue
        wins = sum(1 for value in returns if value > 0)
        win_rate = wins / len(returns)
        volatility = pstdev(returns) if len(returns) > 1 else 0.0
        sharpe = 0.0
        if volatility > 0:
            sharpe = (fmean(returns) / volatility) * math.sqrt(252.0)
        gross_win = sum(value for value in returns if value > 0)
        gross_loss = abs(sum(value for value in returns if value < 0))
        profit_factor = gross_win / gross_loss if gross_loss > 0 else gross_win
        rows.append(
            {
                "model_name": model_name,
                "regime": regime,
                "win_rate": clamp(win_rate),
                "sharpe_ratio": sharpe,
                "average_return": fmean(returns),
                "sample_size": len(returns),
                "profit_factor": profit_factor,
                "max_drawdown": min(returns) if returns else 0.0,
            }
        )

    stored = repository.upsert_model_regime_performance(rows)
    return {"regime_models_updated": len(stored), "buckets": len(buckets)}


def analyze_regimes_for_replay(
    replay_run_id: str,
    *,
    repository: SupabaseRepository | None = None,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    run = repository.get_replay_run(replay_run_id)
    if not run:
        raise ValueError(f"Unknown replay run: {replay_run_id}")
    periods = detect_historical_regime_periods(
        repository=repository,
        replay_run_id=replay_run_id,
        start_date=date.fromisoformat(str(run["start_date"])),
        end_date=date.fromisoformat(str(run["end_date"])),
    )
    stored = persist_historical_regime_periods(periods, repository=repository)
    performance = learn_strategy_performance_by_regime(replay_run_id, repository=repository)
    return {"periods": len(stored), **performance}
