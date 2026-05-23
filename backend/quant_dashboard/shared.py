from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from statistics import fmean
from typing import Any

from backend.core.math_utils import clamp, safe_float


def iso_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def probability_buckets(
    rows: Sequence[Mapping[str, Any]],
    *,
    probability_key: str = "buy_probability",
    outcome_key: str = "outcome",
    bins: int = 10,
) -> list[dict[str, Any]]:
    buckets: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        probability = clamp(safe_float(row.get(probability_key), 0.5))
        index = min(int(probability * bins), bins - 1)
        buckets[index].append(row)

    result = []
    for index in range(bins):
        group = buckets.get(index, [])
        predicted = (index + 0.5) / bins
        wins = sum(1 for row in group if str(row.get(outcome_key)) == "win")
        actual = (wins / len(group)) if group else 0.0
        result.append(
            {
                "bucket": f"{int(predicted * 100)}%",
                "predicted": round(predicted, 3),
                "actual": round(actual, 3),
                "count": len(group),
            }
        )
    return result


def brier_score(rows: Sequence[Mapping[str, Any]], probability_key: str = "buy_probability") -> float:
    if not rows:
        return 0.0
    total = 0.0
    for row in rows:
        probability = clamp(safe_float(row.get(probability_key), 0.5))
        label = 1.0 if str(row.get("outcome")) == "win" else 0.0
        total += (probability - label) ** 2
    return total / len(rows)


def rolling_series(
    values: Sequence[float],
    window: int,
) -> list[dict[str, Any]]:
    if window <= 0:
        return []
    points = []
    for index in range(window - 1, len(values)):
        window_values = values[index - window + 1 : index + 1]
        points.append({"index": index, "value": fmean(window_values)})
    return points
