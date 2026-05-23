from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.auth import AuthUser, get_current_user
from backend.api.deps import get_repository
from backend.audit_center.service import build_audit_center_payload, explain_signal
from backend.calibration_intelligence.service import build_calibration_intelligence_payload
from backend.db.repository import SupabaseRepository
from backend.drift_visualization.service import build_drift_visualization_payload
from backend.infra_observability.service import build_infra_observability_payload
from backend.model_intelligence.service import build_model_intelligence_payload
from backend.notification_analytics.service import build_notification_analytics_payload
from backend.quant_dashboard.overview import build_overview_payload
from backend.regime_analytics.service import build_regime_analytics_payload
from backend.replay_visualization.service import build_replay_visualization_payload
from backend.risk_intelligence.service import build_risk_intelligence_payload
from backend.signal_monitoring.service import build_signal_monitoring_payload


router = APIRouter(prefix="/dashboard", tags=["quant-dashboard"])


@router.get("/overview")
def dashboard_overview(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    return build_overview_payload(repository)


@router.get("/signals")
def dashboard_signals(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
    limit: int = Query(default=1000, ge=1, le=5000),
) -> dict:
    return build_signal_monitoring_payload(repository, signal_limit=limit)


@router.get("/models")
def dashboard_models(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    return build_model_intelligence_payload(repository)


@router.get("/calibration")
def dashboard_calibration(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    return build_calibration_intelligence_payload(repository)


@router.get("/regimes")
def dashboard_regimes(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    return build_regime_analytics_payload(repository)


@router.get("/replay")
def dashboard_replay(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
    replay_run_id: str | None = None,
    snapshot_date: str | None = None,
) -> dict:
    return build_replay_visualization_payload(
        repository,
        replay_run_id=replay_run_id,
        snapshot_date=snapshot_date,
    )


@router.get("/risk")
def dashboard_risk(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    return build_risk_intelligence_payload(repository)


@router.get("/notifications")
def dashboard_notifications(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    return build_notification_analytics_payload(repository)


@router.get("/drift")
def dashboard_drift(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
    refresh: bool = Query(default=False),
) -> dict:
    return build_drift_visualization_payload(repository, refresh=refresh)


@router.get("/infrastructure")
def dashboard_infrastructure(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    return build_infra_observability_payload(repository)


@router.get("/audit")
def dashboard_audit(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    return build_audit_center_payload(repository, limit=limit)


@router.get("/audit/{audit_id}")
def dashboard_audit_detail(
    audit_id: str,
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    explanation = explain_signal(audit_id, repository=repository)
    if not explanation:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return explanation
