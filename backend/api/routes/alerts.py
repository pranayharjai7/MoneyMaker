from fastapi import APIRouter, Depends

from backend.api.auth import AuthUser, get_current_user
from backend.api.deps import get_repository
from backend.api.schemas import AlertOut, AlertsReadRequest, with_stock_alias
from backend.db.repository import SupabaseRepository

router = APIRouter(tags=["alerts"])


@router.get("/alerts", response_model=list[AlertOut])
def get_alerts(
    unread_only: bool = False,
    current_user: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> list[dict]:
    return [
        with_stock_alias(row)
        for row in repository.list_alerts(current_user.id, unread_only=unread_only)
    ]


@router.post("/alerts/read", response_model=list[AlertOut])
def mark_alerts_read(
    payload: AlertsReadRequest,
    current_user: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> list[dict]:
    return [
        with_stock_alias(row)
        for row in repository.mark_alerts_read(current_user.id, payload.alert_ids)
    ]

