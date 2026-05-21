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
