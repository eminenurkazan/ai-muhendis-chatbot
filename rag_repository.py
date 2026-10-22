"""RAG için PostgreSQL arama sınırı."""

from __future__ import annotations

import rag_ticket_pilotu as rag


def search_matches(vector: list[float]) -> list[tuple[float, dict]]:
    return rag.database_matches(vector)
