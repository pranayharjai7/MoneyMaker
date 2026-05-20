from fastapi import APIRouter, Depends

from backend.api.auth import AuthUser, get_current_user
from backend.api.deps import get_repository
from backend.api.schemas import MarketRegimeOut
from backend.db.repository import SupabaseRepository
from backend.regime.service import refresh_market_regime

router = APIRouter(tags=["regime"])


@router.get("/regime", response_model=MarketRegimeOut)
def get_regime(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    return repository.latest_market_regime() or refresh_market_regime(repository=repository)
