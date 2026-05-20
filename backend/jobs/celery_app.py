from __future__ import annotations

from celery import Celery

from backend.core.config import get_settings


settings = get_settings()

celery_app = Celery(
    "moneymaker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["backend.jobs.tasks"],
)

celery_app.conf.timezone = "UTC"
celery_app.conf.task_track_started = True
celery_app.conf.beat_schedule = {
    "daily-market-update": {
        "task": "backend.jobs.tasks.daily_market_update",
        "schedule": 60 * 60 * 24,
    },
    "indicator-recalculation": {
        "task": "backend.jobs.tasks.indicator_recalculation",
        "schedule": 60 * 60 * 24,
    },
    "model-predictions": {
        "task": "backend.jobs.tasks.model_predictions",
        "schedule": 60 * 60 * 24,
    },
    "ensemble-signal-generation": {
        "task": "backend.jobs.tasks.ensemble_signal_generation",
        "schedule": 60 * 60 * 24,
    },
    "weekly-calibration-retraining": {
        "task": "backend.jobs.tasks.calibration_retraining",
        "schedule": 60 * 60 * 24 * 7,
    },
    "market-regime-detection": {
        "task": "backend.jobs.tasks.market_regime_detection",
        "schedule": 60 * 60 * 6,
    },
    "weekly-meta-model-retraining": {
        "task": "backend.jobs.tasks.meta_model_retraining",
        "schedule": 60 * 60 * 24 * 7,
    },
    "portfolio-optimization": {
        "task": "backend.jobs.tasks.portfolio_optimization",
        "schedule": 60 * 60 * 24,
    },
    "paper-trading-simulation": {
        "task": "backend.jobs.tasks.paper_trading_simulation",
        "schedule": 60 * 60 * 24,
    },
    "alert-generation": {
        "task": "backend.jobs.tasks.alert_generation",
        "schedule": 60 * 60 * 24,
    },
    "feedback-evaluation": {
        "task": "backend.jobs.tasks.feedback_evaluation",
        "schedule": 60 * 60 * 24,
    },
}
