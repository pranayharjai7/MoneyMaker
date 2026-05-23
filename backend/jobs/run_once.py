from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Callable

from backend.alerts.service import generate_alerts
from backend.calibration.service import calibrate_recent_predictions
from backend.data_pipeline.service import update_daily_prices
from backend.drift_detection.service import detect_model_drift
from backend.ensemble.service import generate_ensemble_signals
from backend.features.indicators import recalculate_indicators
from backend.feedback.service import evaluate_prediction_outcomes
from backend.jobs.tasks import run_full_signal_pipeline
from backend.meta_model.service import train_meta_model
from backend.models.registry import run_model_predictions
from backend.portfolio.optimizer import optimize_portfolio_weights
from backend.regime.service import refresh_market_regime
from backend.signal_quality.service import evaluate_live_signal_quality
from backend.simulation.engine import run_paper_trading_simulation
from backend.historical_universe import bootstrap_all_universes
from backend.historical_backfill import backfill_universe
from backend.historical_features import generate_features_for_universe
from backend.historical_replay import start_historical_replay
from backend.backfill_orchestrator import orchestrate_historical_pipeline_sync
from backend.bootstrap_training import run_full_bootstrap_training


def _daily_market_update() -> dict[str, int]:
    return asyncio.run(update_daily_prices(lookback_days=10))


def _meta_model_retraining() -> dict[str, object]:
    model = train_meta_model()
    return {
        "meta_model_type": model.model_type,
        "meta_model_training_samples": model.sample_size,
        "sharpe_objective_score": model.sharpe_objective_score,
    }


def _paper_trading_simulation() -> dict[str, object]:
    result = run_paper_trading_simulation()
    return {
        "strategy_return": result["strategy_return"],
        "max_drawdown": result["max_drawdown"],
        "sharpe_ratio": result["sharpe_ratio"],
        "trade_count": result["trade_count"],
    }


def _phase5_bootstrap_universes() -> dict[str, object]:
    return bootstrap_all_universes()


def _phase5_backfill_sample() -> dict[str, object]:
    return asyncio.run(
        backfill_universe("high_liquidity", years=2, max_tickers=3)
    )


def _phase5_generate_features_sample() -> dict[str, object]:
    return generate_features_for_universe("high_liquidity", max_tickers=3)


def _phase5_replay_sample() -> dict[str, object]:
    return start_historical_replay(
        "high_liquidity",
        mode="signal_only",
        years=1,
        max_stocks=3,
    )


def _phase5_full_pipeline_sample() -> dict[str, object]:
    return orchestrate_historical_pipeline_sync(
        "high_liquidity",
        years=1,
        max_stocks=3,
    )


def _phase5_bootstrap_sample() -> dict[str, object]:
    from backend.db.repository import SupabaseRepository

    runs = SupabaseRepository().list_replay_runs(limit=1)
    if not runs:
        raise RuntimeError("No replay runs found. Run phase5_replay_sample first.")
    return run_full_bootstrap_training(str(runs[0]["id"]))


COMMANDS: dict[str, Callable[[], dict[str, object]]] = {
    "daily_market_update": _daily_market_update,
    "indicator_recalculation": recalculate_indicators,
    "model_predictions": run_model_predictions,
    "calibration_retraining": calibrate_recent_predictions,
    "market_regime_detection": refresh_market_regime,
    "meta_model_retraining": _meta_model_retraining,
    "ensemble_signal_generation": generate_ensemble_signals,
    "portfolio_optimization": optimize_portfolio_weights,
    "paper_trading_simulation": _paper_trading_simulation,
    "alert_generation": generate_alerts,
    "feedback_evaluation": evaluate_prediction_outcomes,
    "live_signal_quality_evaluation": evaluate_live_signal_quality,
    "model_drift_detection": detect_model_drift,
    "full_signal_pipeline": run_full_signal_pipeline,
    "phase5_bootstrap_universes": _phase5_bootstrap_universes,
    "phase5_backfill_sample": _phase5_backfill_sample,
    "phase5_generate_features_sample": _phase5_generate_features_sample,
    "phase5_replay_sample": _phase5_replay_sample,
    "phase5_full_pipeline_sample": _phase5_full_pipeline_sample,
    "phase5_bootstrap_sample": _phase5_bootstrap_sample,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run backend jobs once without starting Celery or Redis."
    )
    parser.add_argument("job", choices=sorted(COMMANDS), help="Job to run directly.")
    args = parser.parse_args()
    result = COMMANDS[args.job]()
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
