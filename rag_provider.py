"""Mevcut bulut sağlayıcılarına güvenli erişim; giriş akışını değiştirmez."""

from __future__ import annotations

import re
import time

import rag_ticket_pilotu as rag


class ServiceUnavailable(Exception):
    """Kullanıcıya güvenle gösterilebilecek hazırlık hatası."""


def embed_question(question: str) -> list[float]:
    if not rag.cloudflare_credentials_path().exists():
        raise ServiceUnavailable(
            "Cloudflare bilgileri hazır değil. Önce rag_ticket_pilotu.py dosyasını terminalde bir kez çalıştır."
        )
    account_id, cf_token, _ = rag.cloudflare_credentials()
    try:
        return rag.search.cloud_embeddings(account_id, cf_token, [question])[0]
    except rag.search.PilotError as exc:
        if str(exc).startswith("HTTP 401:"):
            rag.forget_cloudflare_credentials()
            raise ServiceUnavailable("Cloudflare tokenı kabul edilmedi; terminalden yeniden gir.") from None
        raise
    finally:
        del cf_token


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


def answer_from_matches(question: str, matches: list[tuple[float, dict]]) -> dict:
    token = _saved_chatgpt_token()
    try:
        # Kaynak kimlikleri rag.generate_answer -> parse_answer içinde doğrulanır.
        return rag.generate_answer(token, question, matches)
    finally:
        del token
