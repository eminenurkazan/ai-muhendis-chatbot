"""Mevcut RAG yardımcılarını tek, tekrar kullanılabilir soru fonksiyonunda toplar."""

from __future__ import annotations

import re
import time

import rag_ticket_pilotu as rag


class ServiceUnavailable(Exception):
    """API içinde kullanıcıya güvenle gösterilebilecek hazırlık hatası."""


def _saved_chatgpt_token() -> str:
    """Kayıtlı oturumu kullanır; HTTP isteğinde etkileşimli giriş açmaz."""
    if not rag.session_path().exists() or not rag.chat.state_path().exists():
        raise ServiceUnavailable(
            "ChatGPT oturumu hazır değil. Önce rag_ticket_pilotu.py dosyasını terminalde bir kez çalıştır."
        )
    with rag.session_lock():
        state = rag.chat.read_state(rag.chat.state_path())
        saved = rag.read_session(state)
        if saved is None:
            raise ServiceUnavailable("ChatGPT oturumu hazır değil; terminalden yeniden giriş yap.")
        config = rag.auth_config()
        now = time.time()
        if saved["expires_at"] <= now + 120:
            if saved["earliest_refresh_at"] <= now:
                saved = rag.refresh_session(config, state, saved)
                if saved is None:
                    raise ServiceUnavailable("ChatGPT oturumu sona erdi; terminalden yeniden giriş yap.")
            elif saved["expires_at"] <= now + 20:
                raise ServiceUnavailable("Oturum henüz yenilenemiyor; kısa süre sonra tekrar dene.")
        try:
            rag.check_model(saved["access_token"])
        except rag.chat.TestError as exc:
            if not re.search(r": HTTP 401;", str(exc)):
                raise
            saved = rag.refresh_session(config, state, saved)
            if saved is None:
                raise ServiceUnavailable("ChatGPT oturumu sona erdi; terminalden yeniden giriş yap.") from None
            rag.check_model(saved["access_token"])
        return saved["access_token"]


def ask_question(question: str) -> dict:
    """Soru -> embedding -> ilk üç kaynak -> kaynaklı yanıt ve süre."""
    if not isinstance(question, str) or not question.strip() or len(question) > 2000:
        raise ValueError("Soru boş olamaz ve 2000 karakteri geçemez.")
    question = question.strip()
    started = time.perf_counter()

    if not rag.cloudflare_credentials_path().exists():
        raise ServiceUnavailable(
            "Cloudflare bilgileri hazır değil. Önce rag_ticket_pilotu.py dosyasını terminalde bir kez çalıştır."
        )
    account_id, cf_token, _ = rag.cloudflare_credentials()
    try:
        vector = rag.search.cloud_embeddings(account_id, cf_token, [question])[0]
    except rag.search.PilotError as exc:
        if str(exc).startswith("HTTP 401:"):
            rag.forget_cloudflare_credentials()
            raise ServiceUnavailable("Cloudflare tokenı kabul edilmedi; terminalden yeniden gir.") from None
        raise
    finally:
        del cf_token

    matches = rag.database_matches(vector)
    retrieved_ids = [record["issueid"] for _, record in matches]
    token = _saved_chatgpt_token()
    try:
        result = rag.generate_answer(token, question, matches)
    finally:
        del token
    return {
        "answer": result["answer"],
        "used_ticket_ids": result["used_ticket_ids"],
        "insufficient_context": result["insufficient_context"],
        "retrieved_ticket_ids": retrieved_ids,
        "elapsed_ms": round((time.perf_counter() - started) * 1000),
    }
