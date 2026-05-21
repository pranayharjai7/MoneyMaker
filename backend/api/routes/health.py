from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.deps import get_repository
from backend.db.repository import SupabaseRepository
from backend.observability.service import (
    models_health,
    notifications_health,
    realtime_health,
    system_health,
)


router = APIRouter(tags=["health"])


@router.get("/health/system")
def get_system_health(
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    return system_health(repository=repository)


@router.get("/health/models")
def get_models_health(
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    return models_health(repository=repository)


@router.get("/health/realtime")
def get_realtime_health(
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    return realtime_health(repository=repository)


@router.get("/health/notifications")
def get_notifications_health(
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    return notifications_health(repository=repository)
