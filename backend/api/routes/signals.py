from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.auth import AuthUser, get_current_user
from backend.api.deps import get_repository
from backend.api.schemas import SignalOut, with_stock_alias
from backend.db.repository import SupabaseRepository

router = APIRouter(tags=["signals"])


@router.get("/signals", response_model=list[SignalOut])
def list_signals(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> list[dict]:
    return [with_stock_alias(row) for row in repository.list_signals()]


@router.get("/signals/{ticker}", response_model=list[SignalOut])
def get_signals_for_ticker(
    ticker: str,
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> list[dict]:
    stock = repository.get_stock_by_ticker(ticker)
    if not stock:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found.")
    return [with_stock_alias(row) for row in repository.get_signals_for_ticker(ticker)]

