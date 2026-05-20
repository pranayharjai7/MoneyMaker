from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.auth import AuthUser, get_current_user
from backend.api.deps import get_repository
from backend.api.schemas import WatchlistAddRequest, WatchlistItemOut, with_stock_alias
from backend.db.repository import SupabaseRepository

router = APIRouter(tags=["watchlist"])


@router.get("/watchlist", response_model=list[WatchlistItemOut])
def get_watchlist(
    current_user: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> list[dict]:
    return [with_stock_alias(row) for row in repository.list_watchlist(current_user.id)]


@router.post("/watchlist/add", response_model=WatchlistItemOut, status_code=status.HTTP_201_CREATED)
def add_to_watchlist(
    payload: WatchlistAddRequest,
    current_user: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    stock = repository.get_stock_by_ticker(payload.ticker)
    if not stock:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found.")
    item = repository.add_watchlist_stock(current_user.id, stock["id"])
    if not item:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Insert failed.")
    return with_stock_alias({**item, "stock": stock})

