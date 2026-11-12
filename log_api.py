"""Yönetici günlük görüntüleme uçları."""
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

import log_service
from admin_api import require_admin

router = APIRouter(prefix="/admin/logs", tags=["Günlükler"])
Level = Literal["debug", "info", "warning", "error"]


class LogEntry(BaseModel):
    id: str
    created_at: datetime
    level: Level
    event_type: str
    correlation_id: str
    user_email: str | None
    details: dict | list | None


class LogPage(BaseModel):
    items: list[LogEntry]
    next_offset: int | None


class EventCount(BaseModel):
    event_type: str
    count: int


class LogSummary(BaseModel):
    levels: dict[str, int]
    events: list[EventCount]


@router.get("", response_model=LogPage)
def get_logs(days: int = Query(default=7, ge=1, le=365), level: Level | None = None,
             event_type: str | None = Query(default=None, max_length=100), q: str | None = Query(default=None, max_length=100),
             offset: int = Query(default=0, ge=0, le=1_000_000), limit: int = Query(default=50, ge=1, le=100),
             admin: dict = Depends(require_admin)):
    try:
        return log_service.list_logs(days=days, level=level, event_type=event_type, query=q, offset=offset, limit=limit)
    except log_service.LogsUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@router.get("/summary", response_model=LogSummary)
def get_summary(days: int = Query(default=7, ge=1, le=365), admin: dict = Depends(require_admin)):
    try:
        return log_service.summary(days)
    except log_service.LogsUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
