from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.db.repository import SupabaseRepository
from backend.replay_analytics.service import build_replay_performance_report


def build_replay_visualization_payload(
    repository: SupabaseRepository | None = None,
    *,
    replay_run_id: str | None = None,
    snapshot_date: str | None = None,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    runs = repository.list_replay_runs(limit=10)
    if not runs:
        return {
            "runs": [],
            "selected_run_id": None,
            "report": None,
            "scrub_state": None,
            "updated_at": datetime.now(tz=UTC).isoformat(),
        }

    selected_id = replay_run_id or str(runs[0]["id"])
    report = build_replay_performance_report(selected_id, repository=repository)
    snapshots = repository.list_replay_snapshots(replay_run_id=selected_id, limit=500)

    scrub_state = None
    if snapshot_date:
        scrub_state = repository.get_replay_snapshot_at_date(selected_id, snapshot_date)
    elif snapshots:
        scrub_state = snapshots[0]

    drawdown_curve = _drawdown_from_equity(report.get("equity_curve") or [])
    sharpe_evolution = _sharpe_evolution(snapshots)

    return {
        "runs": runs,
        "selected_run_id": selected_id,
        "report": report,
        "drawdown_curve": drawdown_curve,
        "trade_timeline": _trade_timeline(repository, selected_id),
        "sharpe_evolution": sharpe_evolution,
        "scrub_state": scrub_state,
        "available_snapshot_dates": [row.get("snapshot_date") for row in snapshots],
        "updated_at": datetime.now(tz=UTC).isoformat(),
    }


def _drawdown_from_equity(equity_curve: list[dict[str, Any]]) -> list[dict[str, Any]]:
    peak = 0.0
    points = []
    for point in equity_curve:
        equity = float(point.get("equity") or 0.0)
        peak = max(peak, equity)
        drawdown = ((equity / peak) - 1.0) if peak > 0 else 0.0
        points.append({"date": point.get("date"), "drawdown": round(drawdown, 6)})
    return points


def _sharpe_evolution(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "date": row.get("snapshot_date"),
            "sharpe": float(row.get("sharpe") or 0.0),
            "regime": row.get("regime"),
        }
        for row in sorted(snapshots, key=lambda item: str(item.get("snapshot_date")))
    ]


def _trade_timeline(repository: SupabaseRepository, replay_run_id: str) -> list[dict[str, Any]]:
    outcomes = repository.list_replay_outcomes(replay_run_id=replay_run_id, limit=500)
    return [
        {
            "signal_id": row.get("historical_signal_id"),
            "exit_timestamp": row.get("exit_timestamp"),
            "actual_return": row.get("actual_return"),
            "outcome": row.get("outcome"),
        }
        for row in sorted(outcomes, key=lambda item: str(item.get("exit_timestamp")))
    ]
