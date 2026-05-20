from __future__ import annotations

import asyncio

from backend.alerts.service import generate_alerts
from backend.calibration.service import calibrate_recent_predictions
from backend.data_pipeline.service import update_daily_prices
from backend.ensemble.service import generate_ensemble_signals
from backend.features.indicators import recalculate_indicators
from backend.feedback.service import evaluate_prediction_outcomes
from backend.jobs.celery_app import celery_app
from backend.meta_model.service import train_meta_model
from backend.models.registry import run_model_predictions
from backend.portfolio.optimizer import optimize_portfolio_weights
from backend.regime.service import refresh_market_regime
from backend.simulation.engine import run_paper_trading_simulation


@celery_app.task(name="backend.jobs.tasks.daily_market_update")
def daily_market_update() -> dict[str, int]:
    return asyncio.run(update_daily_prices(lookback_days=10))


@celery_app.task(name="backend.jobs.tasks.indicator_recalculation")
def indicator_recalculation() -> dict[str, int]:
    return recalculate_indicators()


@celery_app.task(name="backend.jobs.tasks.model_predictions")
def model_predictions() -> dict[str, int]:
    return run_model_predictions()


@celery_app.task(name="backend.jobs.tasks.ensemble_signal_generation")
def ensemble_signal_generation() -> dict[str, int]:
    return generate_ensemble_signals()


@celery_app.task(name="backend.jobs.tasks.alert_generation")
def alert_generation() -> dict[str, int]:
    return generate_alerts()


@celery_app.task(name="backend.jobs.tasks.feedback_evaluation")
def feedback_evaluation() -> dict[str, int]:
    return evaluate_prediction_outcomes()


@celery_app.task(name="backend.jobs.tasks.calibration_retraining")
def calibration_retraining() -> dict[str, int]:
    return calibrate_recent_predictions()


@celery_app.task(name="backend.jobs.tasks.market_regime_detection")
def market_regime_detection() -> dict[str, object]:
    regime = refresh_market_regime()
    return {"current_regime": regime["current_regime"], "confidence": regime["confidence"]}


@celery_app.task(name="backend.jobs.tasks.meta_model_retraining")
def meta_model_retraining() -> dict[str, object]:
    model = train_meta_model()
    return {
        "meta_model_type": model.model_type,
        "meta_model_training_samples": model.sample_size,
        "sharpe_objective_score": model.sharpe_objective_score,
    }


@celery_app.task(name="backend.jobs.tasks.portfolio_optimization")
def portfolio_optimization() -> dict[str, int]:
    return optimize_portfolio_weights()


@celery_app.task(name="backend.jobs.tasks.paper_trading_simulation")
def paper_trading_simulation() -> dict[str, object]:
    result = run_paper_trading_simulation()
    return {
        "strategy_return": result["strategy_return"],
        "max_drawdown": result["max_drawdown"],
        "sharpe_ratio": result["sharpe_ratio"],
        "trade_count": result["trade_count"],
    }


def run_full_signal_pipeline() -> dict[str, object]:
    market = asyncio.run(update_daily_prices(lookback_days=10))
    indicators = recalculate_indicators()
    predictions = run_model_predictions()
    calibration = calibrate_recent_predictions()
    detected_regime = refresh_market_regime()
    regime = {
        "current_regime": detected_regime["current_regime"],
        "confidence": detected_regime["confidence"],
    }
    signals = generate_ensemble_signals()
    portfolio = optimize_portfolio_weights()
    simulation_result = run_paper_trading_simulation()
    simulation = {
        "strategy_return": simulation_result["strategy_return"],
        "max_drawdown": simulation_result["max_drawdown"],
        "sharpe_ratio": simulation_result["sharpe_ratio"],
        "trade_count": simulation_result["trade_count"],
    }
    alerts = generate_alerts()
    feedback = evaluate_prediction_outcomes()
    return {
        **market,
        **indicators,
        **predictions,
        **calibration,
        **regime,
        **signals,
        **portfolio,
        **simulation,
        **alerts,
        **feedback,
    }


@celery_app.task(name="backend.jobs.tasks.full_signal_pipeline")
def full_signal_pipeline() -> dict[str, int]:
    return run_full_signal_pipeline()
