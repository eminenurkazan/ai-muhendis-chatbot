"""Yerel RAG ve kullanıcı kayıt API'si."""

from __future__ import annotations

import logging
from typing import Literal
from uuid import UUID
from request_replay import replays, ReplayConflict, ReplayBusy

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from conversation import validate_history

import rag_service
from chat_api import router as chat_router
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
logger = logging.getLogger(__name__)


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


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest, user: dict = Depends(require_user)) -> AskResponse:
    """İlk üç ilgili kaynağa dayalı yanıtı ve kullanılan kaynakların atıflarını döndürür."""
    try:
        options = {"expertise_mode": request.expertise_mode}
        if request.history:
            options["history"] = [message.model_dump() for message in request.history]
        def produce():
            return AskResponse(**rag_service.ask_question(request.question, **options))
        if request.request_id is not None:
            return replays.run(user["id"], request.request_id,
                               request.model_dump(mode="json", exclude={"request_id"}), produce)
        return produce()
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
