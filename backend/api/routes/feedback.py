from fastapi import APIRouter, Depends

from backend.api.auth import AuthUser, get_current_user
from backend.api.deps import get_repository
from backend.api.schemas import FeedbackSummaryOut, ModelPerformanceOut
from backend.db.repository import SupabaseRepository
from backend.feedback.service import build_feedback_summary

router = APIRouter(tags=["feedback"])


@router.get("/model-performance", response_model=list[ModelPerformanceOut])
def list_model_performance(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> list[dict]:
    return repository.list_model_performance()


@router.get("/feedback-summary", response_model=FeedbackSummaryOut)
def get_feedback_summary(
    _: AuthUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> dict:
    return build_feedback_summary(repository=repository)
