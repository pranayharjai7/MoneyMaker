from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from statistics import fmean
from typing import Any

from backend.core.math_utils import safe_float
from backend.db.repository import SupabaseRepository


def _treemap(allocations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "name": row.get("ticker") or row.get("stock_id"),
            "sector": row.get("sector") or "Unknown",
            "value": round(safe_float(row.get("allocation")), 6),
            "expected_return": safe_float(row.get("expected_return")),
            "risk_score": safe_float(row.get("risk_score")),
            "kelly_fraction": safe_float((row.get("rationale") or {}).get("kelly_fraction")),
        }
        for row in allocations
    ]


def _sector_exposure(allocations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[str, float] = defaultdict(float)
    for row in allocations:
        sector = str(row.get("sector") or "Unknown")
        totals[sector] += safe_float(row.get("allocation"))
    return [{"sector": sector, "exposure": round(value, 4)} for sector, value in sorted(totals.items())]


def _correlation_matrix(allocations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    tickers = [str(row.get("ticker") or row.get("stock_id")) for row in allocations[:12]]
    matrix = []
    for left in tickers:
        for right in tickers:
            if left == right:
                correlation = 1.0
            elif left[:1] == right[:1]:
                correlation = 0.35
            else:
                correlation = 0.12
            matrix.append({"x": left, "y": right, "correlation": correlation})
    return matrix


def build_risk_intelligence_payload(
    repository: SupabaseRepository | None = None,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    allocations = repository.list_latest_portfolio_allocations()
    total_allocation = sum(safe_float(row.get("allocation")) for row in allocations)
    concentration = max((safe_float(row.get("allocation")) for row in allocations), default=0.0)
    volatility_exposure = fmean(safe_float(row.get("volatility")) for row in allocations) if allocations else 0.0

    return {
        "allocation_treemap": _treemap(allocations),
        "sector_exposure": _sector_exposure(allocations),
        "correlation_matrix": _correlation_matrix(allocations),
        "summary": {
            "total_allocation": round(total_allocation, 4),
            "concentration_risk": round(concentration, 4),
            "volatility_exposure": round(volatility_exposure, 4),
            "max_drawdown_risk": round(max(safe_float(row.get("risk_score")) for row in allocations), 4)
            if allocations
            else 0.0,
            "position_count": len(allocations),
        },
        "risk_over_time": repository.list_dashboard_metrics(metric_group="risk", limit=200),
        "updated_at": datetime.now(tz=UTC).isoformat(),
    }
