"""API'den bağımsız, tekrar kullanılabilir RAG soru hizmeti."""

from __future__ import annotations

import time
from conversation import validate_history
from database.connection import DatabaseError

import request_context
import rag_chain
from async_utils import Busy, StageTimeout, llm_gate, run_blocking, with_timeout
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


STAGE_LABELS = {"embed": "Soru embedding'i", "retrieve": "Kaynak arama", "llm": "Model yanıtı"}


async def ask_question_async(question: str, *, expertise_mode: str = "service_desk", history=None) -> dict:
    """``ask_question`` ile aynı adımlar ve sonuç; olay döngüsünü bloklamaz.

    Aşamalar (embedding → arama → model) sırayla ``await`` edilir, her birinin zaman aşımı vardır ve model
    aşaması eşzamanlılık kapısından geçer. Aşama mantığı ``rag_chain`` adımlarından gelir (tek kaynak).
    """
    if not isinstance(question, str) or not question.strip() or len(question) > 2000:
        raise ValueError("Soru boş olamaz ve 2000 karakteri geçemez.")
    mode = validate_mode(expertise_mode)
    history = validate_history(history)
    clean = question.strip()
    started = time.perf_counter()
    request_context.begin_stages()
    try:
        state = await with_timeout("embed", run_blocking(rag_chain._embed, clean, history=history))
        state = await with_timeout("retrieve", run_blocking(rag_chain._retrieve, state, expertise_mode=mode))
        result = await llm_gate.run(lambda: with_timeout(
            "llm", run_blocking(rag_chain._answer, state, expertise_mode=mode, history=history)))
    except DatabaseError as error:
        raise ServiceUnavailable(str(error)) from None
    except StageTimeout as error:
        raise ServiceUnavailable(f"{STAGE_LABELS.get(error.stage, error.stage)} {error.seconds:g} saniyede "
                                 "tamamlanamadı. Biraz bekleyip tekrar deneyebilirsin.") from None
    except Busy as error:
        raise ServiceUnavailable(str(error)) from None
    result["elapsed_ms"] = round((time.perf_counter() - started) * 1000)
    result["stage_ms"] = request_context.stages_snapshot()
    return result
