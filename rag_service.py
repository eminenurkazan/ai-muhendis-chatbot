"""API'den bağımsız, tekrar kullanılabilir RAG soru hizmeti."""

from __future__ import annotations

import time
from conversation import validate_history
from database.connection import DatabaseError

import request_context
from rag_chain import build_chain
from rag_provider import ServiceUnavailable
from rag_prompts import validate_mode


def ask_question(question: str, *, expertise_mode: str = "service_desk", history=None) -> dict:
    """Soru doğrulama ve süre ölçümü; zincir aynı sonucu üretir."""
    if not isinstance(question, str) or not question.strip() or len(question) > 2000:
        raise ValueError("Soru boş olamaz ve 2000 karakteri geçemez.")
    mode = validate_mode(expertise_mode)
    history = validate_history(history)
    started = time.perf_counter()
    request_context.begin_stages()
    try:
        options = {"expertise_mode": mode}
        if history:
            options["history"] = history
        result = build_chain(**options).invoke(question.strip())
    except DatabaseError as error:
        raise ServiceUnavailable(str(error)) from None
    result["elapsed_ms"] = round((time.perf_counter() - started) * 1000)
    result["stage_ms"] = request_context.stages_snapshot()
    return result
