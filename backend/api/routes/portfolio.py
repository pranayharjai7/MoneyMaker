from fastapi import APIRouter, Depends

from backend.api.auth import AuthUser, get_current_user
from backend.api.deps import get_repository
from backend.api.schemas import PortfolioItemOut, PortfolioWeightOut, with_stock_alias
from backend.db.repository import SupabaseRepository
from backend.portfolio.optimizer import optimize_portfolio_weights

router = APIRouter(tags=["portfolio"])


@router.get("/portfolio", response_model=list[PortfolioItemOut])
def get_portfolio(
    current_user: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> list[dict]:
    return [with_stock_alias(row) for row in repository.list_portfolio(current_user.id)]


@router.get("/portfolio-weights", response_model=list[PortfolioWeightOut])
def get_portfolio_weights(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> list[dict]:
    rows = repository.list_latest_portfolio_allocations()
    if not rows:
        optimize_portfolio_weights(repository=repository)
        rows = repository.list_latest_portfolio_allocations()
    return [with_stock_alias(row) for row in rows]
