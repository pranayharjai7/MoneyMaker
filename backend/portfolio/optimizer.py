from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import numpy as np

from backend.core.math_utils import clamp, safe_float
from backend.db.repository import SupabaseRepository


SEMICONDUCTOR_TICKERS = {
    "NVDA",
    "AMD",
    "AVGO",
    "QCOM",
    "INTC",
    "MU",
    "TSM",
    "ASML",
    "AMAT",
    "LRCX",
    "KLAC",
    "MRVL",
    "ON",
}


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


def _stock(row: Mapping[str, Any]) -> Mapping[str, Any]:
    return row.get("stocks") or row.get("stock") or {}


def _returns(prices: Sequence[Mapping[str, Any]]) -> np.ndarray:
    closes = np.array([safe_float(row.get("close")) for row in prices if safe_float(row.get("close")) > 0])
    if len(closes) < 2:
        return np.array([])
    return np.diff(closes) / closes[:-1]


def _cluster(ticker: str) -> str | None:
    return "semiconductors" if ticker.upper() in SEMICONDUCTOR_TICKERS else None


def _candidate_rows(
    repository: SupabaseRepository,
    signal_limit: int,
) -> list[dict[str, Any]]:
    seen = set()
    candidates = []
    for signal in repository.list_signals(limit=signal_limit):
        stock_id = str(signal.get("stock_id") or "")
        if not stock_id or stock_id in seen:
            continue
        seen.add(stock_id)
        expected_return = safe_float(signal.get("expected_return"))
        probability_edge = safe_float(signal.get("buy_probability"), 0.5) - safe_float(
            signal.get("sell_probability"), 0.5
        )
        if expected_return <= 0 or probability_edge <= 0:
            continue
        stock = _stock(signal)
        ticker = str(stock.get("ticker") or signal.get("ticker") or stock_id).upper()
        indicator = repository.get_indicator_at_or_before(stock_id, str(signal["timestamp"]))
        volatility = max(safe_float((indicator or {}).get("volatility"), 0.02), 0.005)
        risk_score = clamp(safe_float(signal.get("risk_score"), 0.5))
        variance = max(volatility**2, 0.0004)
        fractional_kelly = max(expected_return * probability_edge / variance, 0.0) * 0.25
        raw_allocation = fractional_kelly / (1.0 + risk_score)
        candidates.append(
            {
                "stock_id": stock_id,
                "ticker": ticker,
                "sector": stock.get("sector"),
                "expected_return": expected_return,
                "risk_score": risk_score,
                "volatility": volatility,
                "raw_allocation": raw_allocation,
                "signal_timestamp": _iso(_to_utc_datetime(signal["timestamp"])),
                "score": expected_return * probability_edge / volatility,
            }
        )
    return candidates


def _scale_to_budget(candidates: list[dict[str, Any]]) -> None:
    total = sum(safe_float(row.get("raw_allocation")) for row in candidates)
    if total <= 0:
        return
    for row in candidates:
        row["allocation"] = safe_float(row["raw_allocation"]) / total


def _apply_single_name_cap(candidates: list[dict[str, Any]], max_position: float) -> None:
    for row in candidates:
        row["allocation"] = min(safe_float(row.get("allocation")), max_position)


def _apply_group_cap(candidates: list[dict[str, Any]], key: str, cap: float) -> None:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        value = row.get(key)
        if value:
            grouped[str(value)].append(row)
    for rows in grouped.values():
        total = sum(safe_float(row.get("allocation")) for row in rows)
        if total <= cap or total <= 0:
            continue
        scale = cap / total
        for row in rows:
            row["allocation"] = safe_float(row.get("allocation")) * scale


def _apply_cluster_cap(candidates: list[dict[str, Any]], cap: float) -> None:
    for row in candidates:
        row["cluster"] = _cluster(str(row.get("ticker") or ""))
    _apply_group_cap(candidates, "cluster", cap)


def _apply_correlation_control(
    repository: SupabaseRepository,
    candidates: list[dict[str, Any]],
    correlation_cap: float,
    max_pair_allocation: float,
) -> None:
    returns_by_stock = {
        row["stock_id"]: _returns(repository.get_prices(str(row["stock_id"]), limit=90))
        for row in candidates
    }
    for left_index, left in enumerate(candidates):
        for right in candidates[left_index + 1 :]:
            left_returns = returns_by_stock.get(left["stock_id"], np.array([]))
            right_returns = returns_by_stock.get(right["stock_id"], np.array([]))
            length = min(len(left_returns), len(right_returns))
            if length < 20:
                continue
            correlation = np.corrcoef(left_returns[-length:], right_returns[-length:])[0, 1]
            if np.isnan(correlation) or correlation < correlation_cap:
                continue
            pair_total = safe_float(left.get("allocation")) + safe_float(right.get("allocation"))
            if pair_total <= max_pair_allocation:
                continue
            lower = left if safe_float(left.get("score")) < safe_float(right.get("score")) else right
            lower["allocation"] = max(0.0, safe_float(lower.get("allocation")) - (pair_total - max_pair_allocation))


def _normalize_after_caps(candidates: list[dict[str, Any]]) -> None:
    total = sum(safe_float(row.get("allocation")) for row in candidates)
    if total <= 1.0:
        return
    for row in candidates:
        row["allocation"] = safe_float(row.get("allocation")) / total


def _to_allocation_rows(candidates: list[dict[str, Any]], run_id: str) -> list[dict[str, Any]]:
    return [
        {
            "run_id": run_id,
            "stock_id": row["stock_id"],
            "ticker": row["ticker"],
            "sector": row.get("sector"),
            "allocation": safe_float(row.get("allocation")),
            "expected_return": safe_float(row.get("expected_return")),
            "risk_score": clamp(safe_float(row.get("risk_score"))),
            "volatility": max(0.0, safe_float(row.get("volatility"))),
            "signal_timestamp": row["signal_timestamp"],
            "optimizer_method": "fractional_kelly_vol_scaled",
            "rationale": {
                "score": safe_float(row.get("score")),
                "cluster": row.get("cluster"),
                "raw_allocation": safe_float(row.get("raw_allocation")),
            },
        }
        for row in sorted(candidates, key=lambda item: safe_float(item.get("allocation")), reverse=True)
        if safe_float(row.get("allocation")) > 0
    ]


def optimize_portfolio_weights(
    repository: SupabaseRepository | None = None,
    signal_limit: int = 100,
    max_position: float = 0.12,
    max_sector_exposure: float = 0.35,
    max_semiconductor_exposure: float = 0.20,
    correlation_cap: float = 0.75,
) -> dict[str, int]:
    repository = repository or SupabaseRepository()
    candidates = _candidate_rows(repository, signal_limit=signal_limit)
    if not candidates:
        return {"portfolio_weights": 0}

    _scale_to_budget(candidates)
    _apply_single_name_cap(candidates, max_position=max_position)
    _apply_group_cap(candidates, "sector", max_sector_exposure)
    _apply_cluster_cap(candidates, max_semiconductor_exposure)
    _apply_correlation_control(
        repository,
        candidates,
        correlation_cap=correlation_cap,
        max_pair_allocation=max_position * 1.5,
    )
    _normalize_after_caps(candidates)

    rows = _to_allocation_rows(candidates, run_id=str(uuid4()))
    stored = repository.insert_portfolio_allocations(rows)
    return {"portfolio_weights": len(stored)}
