from __future__ import annotations

import asyncio
from typing import Any, Literal

from backend.bootstrap_training import run_full_bootstrap_training
from backend.db.repository import SupabaseRepository
from backend.historical_backfill import backfill_universe
from backend.historical_features import generate_features_for_universe
from backend.historical_replay import create_replay_run, run_replay
from backend.historical_regimes import analyze_regimes_for_replay
from backend.historical_signals import calibrate_historical_signals, walk_forward_calibration_snapshots
from backend.historical_universe import bootstrap_all_universes, sync_universe

TaskPriority = Literal["backfill", "features", "replay", "training"]


async def orchestrate_historical_pipeline(
    universe_name: str = "high_liquidity",
    *,
    years: int = 5,
    max_stocks: int | None = 50,
    replay_mode: str = "signal_only",
    repository: SupabaseRepository | None = None,
    skip_backfill: bool = False,
    skip_features: bool = False,
) -> dict[str, Any]:
    """Run Phase 5 pipeline end-to-end: universe → backfill → features → replay → training."""
    repository = repository or SupabaseRepository()
    results: dict[str, Any] = {"universe": universe_name}

    results["universe_bootstrap"] = bootstrap_all_universes(repository=repository)
    sync_universe(universe_name, repository=repository)

    if not skip_backfill:
        results["backfill"] = await backfill_universe(
            universe_name,
            years=years,
            max_tickers=max_stocks,
            sync_members=False,
            repository=repository,
        )

    if not skip_features:
        results["features"] = generate_features_for_universe(
            universe_name,
            max_tickers=max_stocks,
            repository=repository,
        )

    run = create_replay_run(
        universe_name,
        mode=replay_mode,  # type: ignore[arg-type]
        years=years,
        max_stocks=max_stocks,
        repository=repository,
    )
    results["replay_run_id"] = run["id"]
    results["replay"] = run_replay(run["id"], repository=repository, resume=False)

    calibrate_historical_signals(run["id"], repository=repository)
    walk_forward_calibration_snapshots(run["id"], repository=repository)
    results["regimes"] = analyze_regimes_for_replay(run["id"], repository=repository)
    results["bootstrap"] = run_full_bootstrap_training(run["id"], repository=repository)

    return results


def orchestrate_historical_pipeline_sync(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return asyncio.run(orchestrate_historical_pipeline(*args, **kwargs))
