"""Yalnızca yönetici rolündeki kullanıcılar için raporlama uçları."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

import admin_service
from async_utils import run_blocking
from auth_api import require_user

router = APIRouter(prefix="/admin", tags=["Yönetim"])


async def require_admin(user: dict = Depends(require_user)) -> dict:
    # Role comes from the current MSSQL record read by require_user, never from the token.
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Bu işlem için yönetici yetkisi gerekir.")
    return user


class TopQuestion(BaseModel):
    question: str
    asked: int
    rated: int
    avg_rating: float | None


class ModeCount(BaseModel):
    expertise_mode: str
    questions: int


class DayCount(BaseModel):
    day: str
    questions: int


class Report(BaseModel):
    days: int
    users_total: int
    users_active: int
    chats: int
    questions: int
    answers: int
    answers_with_sources: int
    avg_latency_ms: int | None
    rated_total: int
    satisfied: int
    rating_distribution: dict[int, int]
    avg_rating: float | None
    satisfaction_rate: float | None
    source_answer_rate: float | None
    rating_coverage: float | None
    top_questions: list[TopQuestion]
    by_mode: list[ModeCount]
    daily: list[DayCount]


@router.get("/report", response_model=Report)
async def get_report(days: int = Query(default=30, ge=1, le=365), top: int = Query(default=10, ge=1, le=50),
                     admin: dict = Depends(require_admin)):
    try:
        return await run_blocking(admin_service.report, days, top)
    except admin_service.ReportUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
