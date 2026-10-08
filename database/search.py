"""pgvector üzerinde cosine benzerliğiyle bilgi arama."""

from __future__ import annotations

from pgvector import Vector

from .connection import connect


def search_chunks(
    query_vector: list[float],
    *,
    embedding_model: str,
    limit: int = 3,
) -> list[tuple[float, dict[str, object]]]:
    """Soru vektörünü knowledge_chunks.embedding ile karşılaştırır."""

    embedding = Vector(query_vector)
    rows = []
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT
                1 - (c.embedding <=> %s) AS cosine_similarity,
                c.id AS chunk_id,
                s.name AS source_name,
                s.source_url,
                r.source_record_id,
                r.problem,
                r.category,
                r.solution,
                r.resolution,
                r.resolution_confirmed,
                r.source_comment_seq,
                r.solution_scope,
                r.limitations
            FROM knowledge_chunks AS c
            JOIN knowledge_records AS r ON r.id = c.record_id
            JOIN knowledge_sources AS s ON s.id = r.source_id
            WHERE r.review_status = 'approved'
              AND r.index_status = 'ready'
              AND c.embedding_model = %s
            ORDER BY c.embedding <=> %s
            LIMIT %s
            """,
            (embedding, embedding_model, embedding, limit),
        ).fetchall()

    matches: list[tuple[float, dict[str, object]]] = []
    for row in rows:
        (
            similarity,
            chunk_id,
            source_name,
            source_url,
            source_record_id,
            problem,
            category,
            solution,
            resolution,
            resolution_confirmed,
            source_comment_seq,
            solution_scope,
            limitations,
        ) = row
        record = {
            "issueid": str(source_record_id),
            "problem": problem,
            "category": category or "",
            "solution": solution,
            "resolution": resolution or "",
            "resolution_confirmed": (
                "" if resolution_confirmed is None else str(resolution_confirmed).lower()
            ),
            "source_comment_seq": source_comment_seq or {},
            "solution_scope": solution_scope or "",
            "limitations": limitations or "",
            "chunk_id": str(chunk_id),
            "source_name": source_name,
            "source_url": source_url or "",
        }
        matches.append((float(similarity), record))
    return matches
