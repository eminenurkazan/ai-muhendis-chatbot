"""RAG için PostgreSQL arama sınırı ve uzmanlık alanı seçimi."""
from __future__ import annotations

import rag_ticket_pilotu as rag
from rag_prompts import validate_mode


def search_matches(vector: list[float], *, expertise_mode: str = 'service_desk') -> list[tuple[float, dict]]:
    mode=validate_mode(expertise_mode)
    if mode=='service_desk':
        return rag.database_matches(vector)
    return rag.database_matches(vector,domains=('general_it',mode))
