"""Yerel RAG API'si: tek soru-yanıt endpoint'i."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import rag_service


class Utf8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"


app = FastAPI(
    title="Ticket RAG Pilot API",
    version="0.1.0",
    default_response_class=Utf8JSONResponse,
)
logger = logging.getLogger(__name__)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class AskResponse(BaseModel):
    answer: str
    used_ticket_ids: list[str]
    insufficient_context: bool
    retrieved_ticket_ids: list[str]
    elapsed_ms: int


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    """Aranan ilk üç ticketı ve yalnızca onlara dayalı yanıtı döndürür."""
    try:
        return AskResponse(**rag_service.ask_question(request.question))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except rag_service.ServiceUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except Exception as exc:
        # Token, ham servis yanıtı veya veritabanı bağlantı dizesi sızdırma.
        logger.error("RAG isteği tamamlanamadı: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Yanıt üretilemedi; terminal çıktısını kontrol et.") from None
