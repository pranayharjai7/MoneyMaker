from fastapi import APIRouter, Depends

from backend.api.auth import AuthUser, get_current_user
from backend.api.deps import get_repository
from backend.api.schemas import BacktestResultOut
from backend.db.repository import SupabaseRepository
from backend.simulation.engine import run_paper_trading_simulation

router = APIRouter(tags=["simulation"])


@router.get("/backtest-results", response_model=BacktestResultOut)
def get_backtest_results(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    return repository.latest_backtest_result() or run_paper_trading_simulation(repository=repository)
