from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.auth import AuthUser, get_current_user
from backend.api.deps import get_repository
from backend.db.repository import SupabaseRepository
from backend.drift_detection.service import build_drift_report
from backend.guardrails.service import build_guardrail_report
from backend.notification_control.service import build_notification_engagement_report
from backend.paper_analytics.service import (
    build_paper_performance_report,
    paper_equity_curve,
    paper_history,
    paper_regime_adjusted_returns,
)
from backend.signal_quality.service import build_signal_quality_report


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/signals")
def signal_quality(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    report = build_signal_quality_report(repository=repository)
    report["guardrails"] = build_guardrail_report(repository=repository)
    return report


@router.get("/models")
def model_performance(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    return {
        "model_performance": repository.list_model_performance(),
        "drift": build_drift_report(repository=repository),
    }


@router.get("/regimes")
def regime_analytics(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    return {
        "latest_regime": repository.latest_market_regime(),
        "model_regime_performance": repository.list_model_regime_performance(),
    }


@router.get("/notifications")
def notification_engagement(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    return build_notification_engagement_report(repository=repository)


@router.get("/paper-performance")
def paper_performance(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    return build_paper_performance_report(repository=repository)


@router.get("/paper-history")
def paper_trading_history(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> list[dict]:
    return paper_history(repository=repository)


@router.get("/paper-equity-curve")
def paper_trading_equity_curve(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> list[dict]:
    return paper_equity_curve(repository=repository)


@router.get("/paper-regime-returns")
def paper_trading_regime_returns(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> list[dict]:
    return paper_regime_adjusted_returns(repository=repository)
