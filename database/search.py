"""Ortak pgvector havuzunda onaylı bilgi arama; isteğe bağlı alan filtresi."""
from __future__ import annotations

from pgvector import Vector
from .connection import connect


def search_chunks(query_vector: list[float], *, embedding_model: str, limit: int = 3,
                  domains: tuple[str, ...] | None = None) -> list[tuple[float, dict[str, object]]]:
    if domains is not None and (not domains or any(d not in {'general_it','windows_server','oracle_db'} for d in domains)):
        raise ValueError('Arama alanları geçersiz.')
    embedding=Vector(query_vector)
    allowed=list(domains) if domains is not None else None
    with connect() as connection:
        rows=connection.execute("""
            SELECT 1 - (c.embedding <=> %s), c.id, s.name, s.source_url,
                r.source_record_id,r.problem,r.category,r.solution,r.resolution,
                r.resolution_confirmed,r.source_comment_seq,r.solution_scope,r.limitations,
                r.record_type,r.domain,r.title,r.metadata
            FROM knowledge_chunks c
            JOIN knowledge_records r ON r.id=c.record_id
            JOIN knowledge_sources s ON s.id=r.source_id
            WHERE r.review_status='approved' AND r.index_status='ready'
              AND c.embedding_model=%s
              AND c.record_content_hash=r.content_hash
              AND (%s::text[] IS NULL OR r.domain=ANY(%s::text[]))
            ORDER BY c.embedding <=> %s LIMIT %s
            """,(embedding,embedding_model,allowed,allowed,embedding,limit)).fetchall()
    matches=[]
    for row in rows:
        (similarity,chunk_id,source_name,source_url,record_id,problem,category,solution,resolution,
         confirmed,comment_seq,scope,limitations,record_type,domain,title,metadata)=row
        record={
            # issueid eski API/pilotla uyumluluk için ortak kaynak kimliğinin takma adı.
            'issueid':str(record_id),'source_record_id':str(record_id),
            'record_type':record_type,'domain':domain,'title':title or '',
            'problem':problem,'category':category or '', 'solution':solution,
            'resolution':resolution or '',
            'resolution_confirmed':'' if confirmed is None else str(confirmed).lower(),
            'source_comment_seq':comment_seq or {},'solution_scope':scope or '',
            'limitations':limitations or '', 'chunk_id':str(chunk_id),'source_name':source_name,
            'source_url':metadata.get('question_url') or source_url or '',
        }
        for key in ('answer_url','question_author','answer_author','question_license','answer_license',
                    'question_license_url','answer_license_url','official_verification_status','official_sources',
                    'official_context','product_version_environment','source_evidence','transformation'):
            if key in metadata:
                record[key]=metadata[key]
        # raw_text ve özgün tam cevap hiçbir zaman model bağlamına alınmaz.
        matches.append((float(similarity),record))
    return matches
