"""Yerel RAG ve kullanıcı kayıt API'si."""

from __future__ import annotations

import logging
import time
from typing import Literal
from uuid import UUID
from request_replay import replays, ReplayConflict, ReplayBusy

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from conversation import validate_history

import app_log
import request_context
import rag_service
import chat_service
from chat_api import router as chat_router
from admin_api import router as admin_router
from kb_api import router as kb_router
from log_api import router as log_router
from auth_api import require_user, router as auth_router
from registration_api import router as registration_router
from rag_prompts import ExpertiseMode


class Utf8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"


app = FastAPI(
    title="Ticket RAG Pilot API",
    version="0.3.0",
    default_response_class=Utf8JSONResponse,
)
app.include_router(registration_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(admin_router)
app.include_router(kb_router)
app.include_router(log_router)
logger = logging.getLogger(__name__)


@app.middleware("http")
async def correlation_middleware(request, call_next):
    """Her isteğe korelasyon kimliği verir; 5xx yanıtlarını ve yakalanmamış hataları günlüğe yazar."""
    correlation = request_context.new_correlation()
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as error:
        app_log.log_event("error", "http.unhandled_exception", correlation_id=correlation, details={
            "method": request.method, "path": request.url.path, "error": type(error).__name__,
            "duration_ms": round((time.perf_counter() - started) * 1000)})
        raise
    response.headers["X-Request-ID"] = correlation
    if response.status_code >= 500:
        app_log.log_event("error", "http.server_error", correlation_id=correlation, details={
            "method": request.method, "path": request.url.path, "status": response.status_code,
            "duration_ms": round((time.perf_counter() - started) * 1000)})
    return response


class ConversationMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    expertise_mode: ExpertiseMode = "service_desk"
    request_id: UUID | None = None
    history: list[ConversationMessage] = Field(default_factory=list, max_length=6)

    @model_validator(mode="after")
    def check_history(self):
        validate_history([message.model_dump() for message in self.history])
        return self


class AskResponse(BaseModel):
    answer: str
    used_ticket_ids: list[str]
    insufficient_context: bool
    retrieved_ticket_ids: list[str]
    elapsed_ms: int
    expertise_mode: ExpertiseMode
    prompt_version: str
    used_source_ids: list[str]
    retrieved_source_ids: list[str]
    sources: list[dict[str, object]]


class SavedAskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=2000)
    request_id: UUID


def _log_ask_failure(user, chat_id, status, error, started):
    app_log.log_event("error" if status >= 500 else "warning", "chat.ask_failed", user_id=user["id"], details={
        "chat_id": str(chat_id) if chat_id else None, "status": status, "error": type(error).__name__,
        "duration_ms": round((time.perf_counter() - started) * 1000)})


@app.post("/chats/{chat_id}/ask", response_model=AskResponse)
async def ask_saved(chat_id: UUID, request: SavedAskRequest, user: dict = Depends(require_user)):
    """History and expertise come from the authenticated user's saved chat. Async: no blocking call on the loop."""
    captured = {}
    started = time.perf_counter()

    async def generate(question, **options):
        result = await rag_service.ask_question_async(question, **options)
        captured["stage_ms"] = result.get("stage_ms")
        return AskResponse(**result).model_dump(mode="json")
    try:
        response = await chat_service.answer_chat_async(str(user["id"]), str(chat_id), request.question,
                                                        str(request.request_id), generate)
    except chat_service.ChatNotFound as error:
        _log_ask_failure(user, chat_id, 404, error, started)
        raise HTTPException(status_code=404, detail=str(error)) from None
    except (chat_service.ChatUnavailable, rag_service.ServiceUnavailable, ReplayBusy) as error:
        _log_ask_failure(user, chat_id, 503, error, started)
        raise HTTPException(status_code=503, detail=str(error)) from None
    except ReplayConflict as error:
        _log_ask_failure(user, chat_id, 409, error, started)
        raise HTTPException(status_code=409, detail=str(error)) from None
    except ValueError as error:
        _log_ask_failure(user, chat_id, 422, error, started)
        raise HTTPException(status_code=422, detail=str(error)) from None
    except Exception as error:
        logger.error("Sohbet isteği tamamlanamadı: %s", type(error).__name__)
        _log_ask_failure(user, chat_id, 502, error, started)
        raise HTTPException(status_code=502, detail="Yanıt üretilemedi veya kaydedilemedi. Tekrar deneyebilirsin.") from None
    # Soru ve yanıt metni günlüğe yazılmaz; yalnız ölçümler ve sayılar.
    app_log.log_event("info", "chat.ask_completed", user_id=user["id"], details={
        "chat_id": str(chat_id), "mode": response.get("expertise_mode"), "elapsed_ms": response.get("elapsed_ms"),
        "insufficient_context": response.get("insufficient_context"),
        "used_sources": len(response.get("used_source_ids") or []), "stage_ms": captured.get("stage_ms"),
        "replayed": not captured})
    return response


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest, user: dict = Depends(require_user)) -> AskResponse:
    """İlk üç ilgili kaynağa dayalı yanıtı ve kullanılan kaynakların atıflarını döndürür."""
    try:
        options = {"expertise_mode": request.expertise_mode}
        if request.history:
            options["history"] = [message.model_dump() for message in request.history]

        async def produce():
            return AskResponse(**await rag_service.ask_question_async(request.question, **options))
        if request.request_id is not None:
            return await replays.run_async(user["id"], request.request_id,
                                           request.model_dump(mode="json", exclude={"request_id"}), produce)
        return await produce()
    except ReplayConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except ReplayBusy as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except rag_service.ServiceUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except Exception as exc:
        # Token, ham servis yanıtı veya veritabanı bağlantı dizesi sızdırma.
        logger.error("RAG isteği tamamlanamadı: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Yanıt üretilemedi; terminal çıktısını kontrol et.") from None


@app.get("/health", tags=["Durum"])
async def health():
    """Veritabanına dokunmayan hafif canlılık kontrolü; olay döngüsünün yanıt verdiğini gösterir."""
    return {"status": "ok"}
