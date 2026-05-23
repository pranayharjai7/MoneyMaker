from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from backend.db.repository import SupabaseRepository
from backend.historical_replay.engine import ReplayConfig, ReplayMode, run_replay


def create_replay_run(
    universe_name: str,
    *,
    mode: ReplayMode = "signal_only",
    years: int = 2,
    start_date: date | None = None,
    end_date: date | None = None,
    max_stocks: int | None = 25,
    meta_model_version: str = "replay_v1",
    repository: SupabaseRepository | None = None,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=max(years, 1) * 365))
    config = ReplayConfig(
        universe_name=universe_name,
        mode=mode,
        start_date=start,
        end_date=end,
        years=years,
        max_stocks=max_stocks,
        meta_model_version=meta_model_version,
    )
    return repository.create_replay_run(
        universe_name=universe_name,
        mode=mode,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        meta_model_version=meta_model_version,
        config={
            "years": years,
            "max_stocks": max_stocks,
            "checkpoint_every_days": config.checkpoint_every_days,
            "initial_cash": config.initial_cash,
        },
    )


def start_historical_replay(
    universe_name: str = "high_liquidity",
    *,
    mode: ReplayMode = "signal_only",
    years: int = 2,
    max_stocks: int | None = 10,
    resume: bool = True,
    repository: SupabaseRepository | None = None,
) -> dict[str, Any]:
    """Create a replay run and execute it (requires backfilled prices + features)."""
    repository = repository or SupabaseRepository()
    run = create_replay_run(
        universe_name,
        mode=mode,
        years=years,
        max_stocks=max_stocks,
        repository=repository,
    )
    summary = run_replay(run["id"], repository=repository, resume=resume)
    return {"replay_run_id": run["id"], **summary}


def resume_historical_replay(
    replay_run_id: str,
    *,
    repository: SupabaseRepository | None = None,
) -> dict[str, Any]:
    repository = repository or SupabaseRepository()
    summary = run_replay(replay_run_id, repository=repository, resume=True)
    return {"replay_run_id": replay_run_id, **summary}
