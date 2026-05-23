from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from backend.core.math_utils import safe_float
from backend.db.repository import SupabaseRepository


def _regime_timeline(periods: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "regime": row.get("regime"),
            "start_date": row.get("start_date"),
            "end_date": row.get("end_date"),
            "confidence": safe_float(row.get("confidence")),
        }
        for row in sorted(periods, key=lambda item: str(item.get("start_date")))
    ]


def _strategy_heatmap(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    matrix: dict[str, dict[str, float]] = defaultdict(dict)
    for row in rows:
        model = str(row.get("model_name"))
        regime = str(row.get("regime"))
        matrix[model][regime] = round(safe_float(row.get("sharpe_ratio")), 4)
    return [{"strategy": model, **regimes} for model, regimes in sorted(matrix.items())]


def build_regime_analytics_payload(
    repository: SupabaseRepository | None = None,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    latest = repository.latest_market_regime()
    performance = repository.list_model_regime_performance()
    periods = repository.list_historical_regime_periods(limit=200)

    transitions = []
    ordered = _regime_timeline(periods)
    for index in range(1, len(ordered)):
        previous = ordered[index - 1]["regime"]
        current = ordered[index]["regime"]
        if previous != current:
            transitions.append(
                {
                    "from": previous,
                    "to": current,
                    "at": ordered[index]["start_date"],
                }
            )

    return {
        "current": {
            "regime": (latest or {}).get("current_regime"),
            "confidence": safe_float((latest or {}).get("confidence")),
            "volatility_proxy": safe_float((latest or {}).get("volatility_proxy")),
        },
        "timeline": ordered if ordered else _live_timeline_from_performance(performance),
        "transitions": transitions,
        "strategy_performance_heatmap": _strategy_heatmap(performance),
        "model_regime_performance": performance,
        "updated_at": datetime.now(tz=UTC).isoformat(),
    }


def _live_timeline_from_performance(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    regimes = sorted({str(row.get("regime")) for row in rows if row.get("regime")})
    return [{"regime": regime, "start_date": None, "end_date": None, "confidence": 0.0} for regime in regimes]
