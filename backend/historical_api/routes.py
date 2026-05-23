from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.auth import AuthUser, get_current_user
from backend.api.deps import get_repository
from backend.db.repository import SupabaseRepository
from backend.historical_regimes.service import detect_historical_regime_periods, learn_strategy_performance_by_regime
from backend.historical_signals.service import summarize_historical_signals
from backend.replay_analytics.service import build_replay_performance_report


router = APIRouter(prefix="/historical", tags=["historical"])


def _resolve_replay_run_id(
    repository: SupabaseRepository,
    replay_run_id: str | None,
) -> str:
    if replay_run_id:
        run = repository.get_replay_run(replay_run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Replay run not found")
        return replay_run_id

    runs = repository.list_replay_runs(limit=1)
    if not runs:
        raise HTTPException(status_code=404, detail="No historical replay runs available")
    return str(runs[0]["id"])


@router.get("/performance")
def historical_performance(
    replay_run_id: str | None = Query(default=None),
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    run_id = _resolve_replay_run_id(repository, replay_run_id)
    return build_replay_performance_report(run_id, repository=repository)


@router.get("/equity-curve")
def historical_equity_curve(
    replay_run_id: str | None = Query(default=None),
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    report = build_replay_performance_report(
        _resolve_replay_run_id(repository, replay_run_id),
        repository=repository,
    )
    return {
        "replay_run_id": report["replay_run_id"],
        "equity_curve": report["equity_curve"],
        "cumulative_return": report["cumulative_return"],
    }


@router.get("/regimes")
def historical_regimes(
    replay_run_id: str | None = Query(default=None),
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    run_id = _resolve_replay_run_id(repository, replay_run_id)
    run = repository.get_replay_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Replay run not found")
    from datetime import date

    periods = repository.list_historical_regime_periods(replay_run_id=run_id)
    if not periods:
        periods = detect_historical_regime_periods(
            repository=repository,
            replay_run_id=run_id,
            start_date=date.fromisoformat(str(run["start_date"])),
            end_date=date.fromisoformat(str(run["end_date"])),
        )
    return {
        "replay_run_id": run_id,
        "periods": periods,
        "model_regime_performance": repository.list_model_regime_performance(),
    }


@router.get("/calibration")
def historical_calibration(
    replay_run_id: str | None = Query(default=None),
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    run_id = _resolve_replay_run_id(repository, replay_run_id)
    report = build_replay_performance_report(run_id, repository=repository)
    return {
        "replay_run_id": run_id,
        "calibration_timeline": report["calibration_timeline"],
        "signal_summary": summarize_historical_signals(run_id, repository=repository),
        "snapshots": repository.list_historical_calibration_snapshots(replay_run_id=run_id),
    }


@router.get("/strategy-performance")
def historical_strategy_performance(
    replay_run_id: str | None = Query(default=None),
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    run_id = _resolve_replay_run_id(repository, replay_run_id)
    report = build_replay_performance_report(run_id, repository=repository)
    regime_stats = learn_strategy_performance_by_regime(run_id, repository=repository)
    return {
        "replay_run_id": run_id,
        "strategy_contribution": report["strategy_contribution"],
        "regime_breakdown": report["regime_breakdown"],
        "model_regime_performance": repository.list_model_regime_performance(),
        "regime_learning": regime_stats,
    }
