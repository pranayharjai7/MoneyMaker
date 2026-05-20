from fastapi import APIRouter, Depends

from backend.api.auth import AuthUser, get_current_user
from backend.api.deps import get_repository
from backend.api.schemas import CalibrationStatusOut
from backend.calibration.service import build_calibration_status
from backend.db.repository import SupabaseRepository

router = APIRouter(tags=["calibration"])


@router.get("/calibration-status", response_model=CalibrationStatusOut)
def get_calibration_status(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    return build_calibration_status(repository=repository)
