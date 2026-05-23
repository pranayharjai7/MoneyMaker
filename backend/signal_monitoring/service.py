from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from statistics import fmean
from typing import Any

from backend.core.math_utils import clamp, safe_float
from backend.db.repository import SupabaseRepository
from backend.quant_dashboard.shared import probability_buckets


def _enrich_signal(signal: Mapping[str, Any], regime: str | None) -> dict[str, Any]:
    stock = signal.get("stocks") or {}
    ticker = stock.get("ticker") or signal.get("ticker") or "UNKNOWN"
    buy_probability = clamp(safe_float(signal.get("buy_probability"), 0.5))
    sell_probability = clamp(safe_float(signal.get("sell_probability"), 0.5))
    signal_type = str(signal.get("signal_type") or "neutral").upper()
    return {
        "id": signal.get("id"),
        "ticker": ticker,
        "signal_type": signal_type,
        "buy_probability": buy_probability,
        "sell_probability": sell_probability,
        "probability": max(buy_probability, sell_probability),
        "expected_return": safe_float(signal.get("expected_return")),
        "risk_score": safe_float(signal.get("risk_score")),
        "regime": regime or "UNKNOWN",
        "confidence": clamp(max(buy_probability, sell_probability)),
        "model_agreement": clamp(1.0 - abs(buy_probability - sell_probability)),
        "timestamp": signal.get("timestamp"),
        "sector": stock.get("sector"),
    }


def _signal_frequency(signals: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_day: dict[str, int] = defaultdict(int)
    for signal in signals:
        timestamp = signal.get("timestamp")
        if not timestamp:
            continue
        day = str(timestamp)[:10]
        by_day[day] += 1
    return [{"date": day, "count": count} for day, count in sorted(by_day.items())]


def _sharpe_by_signal_type(live_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in live_rows:
        signal_type = str(row.get("model_used") or row.get("signal_type") or "ensemble")
        grouped[signal_type].append(safe_float(row.get("pnl")))
    result = []
    for signal_type, pnls in grouped.items():
        if len(pnls) < 2:
            sharpe = 0.0
        else:
            mean = fmean(pnls)
            variance = fmean((value - mean) ** 2 for value in pnls)
            sharpe = (mean / variance**0.5) if variance > 0 else 0.0
        result.append({"signal_type": signal_type, "sharpe": round(sharpe, 4), "count": len(pnls)})
    return sorted(result, key=lambda row: row["sharpe"], reverse=True)


def build_signal_monitoring_payload(
    repository: SupabaseRepository | None = None,
    *,
    signal_limit: int = 1000,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    regime = repository.latest_market_regime()
    regime_name = str((regime or {}).get("current_regime") or "UNKNOWN")
    signals = repository.list_signals(limit=signal_limit)
    live_rows = repository.list_live_signal_performance(limit=signal_limit)

    feed = [_enrich_signal(signal, regime_name) for signal in signals[:50]]
    quality_buckets = probability_buckets(
        [
            {
                "buy_probability": safe_float(row.get("predicted_return"), 0.5),
                "outcome": row.get("outcome"),
            }
            for row in live_rows
        ]
    )

    return {
        "live_feed": feed,
        "summary": {
            "active_signals": len([row for row in feed if row["signal_type"] != "NEUTRAL"]),
            "latest_regime": regime_name,
            "regime_confidence": safe_float((regime or {}).get("confidence")),
        },
        "quality": {
            "win_rate_by_probability_bucket": quality_buckets,
            "sharpe_by_signal_type": _sharpe_by_signal_type(live_rows),
            "signal_frequency": _signal_frequency(signals),
        },
        "updated_at": datetime.now(tz=UTC).isoformat(),
    }
