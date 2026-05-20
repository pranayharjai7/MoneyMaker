from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.auth import AuthUser, get_current_user
from backend.api.deps import get_repository
from backend.api.schemas import StockOut
from backend.db.repository import SupabaseRepository

router = APIRouter(tags=["stocks"])


@router.get("/stocks", response_model=list[StockOut])
def list_stocks(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> list[dict]:
    return repository.list_stocks()


@router.get("/stocks/{ticker}", response_model=StockOut)
def get_stock(
    ticker: str,
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    stock = repository.get_stock_by_ticker(ticker)
    if not stock:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found.")
    return stock

