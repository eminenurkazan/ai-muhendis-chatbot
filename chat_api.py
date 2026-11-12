"""Chat metadata and history endpoints; identity always comes from JWT."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

import app_log
from auth_api import require_user
import chat_service as service
from rag_prompts import ExpertiseMode


router = APIRouter(prefix="/chats", tags=["Sohbet geçmişi"])


class CreateChat(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(default="Yeni sohbet", min_length=1, max_length=200)
    expertise_mode: ExpertiseMode = "service_desk"

    @field_validator("title")
    @classmethod
    def clean_title(cls, value):
        if not value.strip():
            raise ValueError("Sohbet başlığı boş olamaz.")
        return value.strip()


class ChatInfo(BaseModel):
    id: UUID
    title: str | None
    expertise_mode: ExpertiseMode
    created_at: datetime
    updated_at: datetime


class ChatPage(BaseModel):
    items: list[ChatInfo]
    next_offset: int | None


class SavedMessage(BaseModel):
    id: UUID
    message_seq: int
    role: Literal["user", "assistant"]
    content: str
    message_status: Literal["pending", "completed", "error"]
    request_id: UUID | None
    citations: list
    sources: list
    model_name: str | None
    created_at: datetime
    feedback_rating: int | None = None
    feedback_comment: str | None = None


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rating: int = Field(strict=True, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class FeedbackInfo(BaseModel):
    rating: int
    comment: str | None


class MessagePage(BaseModel):
    items: list[SavedMessage]
    next_after_seq: int | None


def _call(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except service.ChatNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except service.ChatUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from None


@router.post("", status_code=201, response_model=ChatInfo)
def create_chat(request: CreateChat, user: dict = Depends(require_user)):
    return _call(service.create_chat, str(user["id"]), request.title, request.expertise_mode)


@router.get("", response_model=ChatPage)
def list_chats(offset: int = Query(default=0, ge=0, le=100000),
               limit: int = Query(default=50, ge=1, le=100), user: dict = Depends(require_user)):
    return _call(service.list_chats, str(user["id"]), offset, limit)


@router.get("/{chat_id}", response_model=ChatInfo)
def get_chat(chat_id: UUID, user: dict = Depends(require_user)):
    return _call(service.get_chat, str(user["id"]), str(chat_id))


@router.get("/{chat_id}/messages", response_model=MessagePage)
def list_messages(chat_id: UUID, after_seq: int = Query(default=0, ge=0, le=2147483647),
                  limit: int = Query(default=50, ge=1, le=100), user: dict = Depends(require_user)):
    return _call(service.list_messages, str(user["id"]), str(chat_id), after_seq, limit)


@router.put("/{chat_id}/requests/{request_id}/feedback", response_model=FeedbackInfo)
def save_feedback(chat_id: UUID, request_id: UUID, request: FeedbackRequest,
                  user: dict = Depends(require_user)):
    saved = _call(service.save_feedback, str(user["id"]), str(chat_id), str(request_id),
                  request.rating, request.comment)
    # Yorum metni günlüğe yazılmaz.
    app_log.log_event("info", "chat.feedback_saved", user_id=str(user["id"]), details={
        "chat_id": str(chat_id), "rating": request.rating, "has_comment": bool(request.comment)})
    return saved
