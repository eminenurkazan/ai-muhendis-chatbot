"""API'den bağımsız, tekrar kullanılabilir RAG soru hizmeti."""

from __future__ import annotations

import time

from rag_chain import build_chain
from rag_provider import ServiceUnavailable
from rag_prompts import validate_mode


def ask_question(question: str, *, expertise_mode: str = "service_desk") -> dict:
    """Soru doğrulama ve süre ölçümü; zincir aynı sonucu üretir."""
    if not isinstance(question, str) or not question.strip() or len(question) > 2000:
        raise ValueError("Soru boş olamaz ve 2000 karakteri geçemez.")
    mode = validate_mode(expertise_mode)
    started = time.perf_counter()
    result = build_chain(expertise_mode=mode).invoke(question.strip())
    result["elapsed_ms"] = round((time.perf_counter() - started) * 1000)
    return result
