"""10 pilot ticketı ve hazır embedding'lerini PostgreSQL'e aktarır.

Embedding üretmez. Önce mevcut pilotun oluşturduğu
outputs_local/ticket_vektorleri.json cache'i kullanılmalıdır.
Aynı kaynak ve issueid ile tekrar çalıştırıldığında kayıtlar çoğalmaz.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from psycopg.types.json import Jsonb

import ticket_vektor_arama as pilot
from .connection import DatabaseError, connect


SOURCE_NAME = "Mendeley Service Desk Tickets"
SOURCE_TYPE = "ticket_dataset"
SOURCE_VERSION = "pilot-10-2026-10-01"
EMBEDDING_MODEL = pilot.MODEL


def content_hash(record: dict[str, str]) -> str:
    canonical = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_json_object(value: str, field_name: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name} alanı geçerli JSON değil.") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{field_name} alanı JSON nesnesi olmalı.")
    return parsed


def upsert_source(connection) -> str:
    row = connection.execute(
        """
        INSERT INTO knowledge_sources
            (name, source_type, source_version)
        VALUES (%s, %s, %s)
        ON CONFLICT (name, source_version)
        DO UPDATE SET source_type = EXCLUDED.source_type
        RETURNING id
        """,
        (SOURCE_NAME, SOURCE_TYPE, SOURCE_VERSION),
    ).fetchone()
    return str(row[0])


def upsert_record(connection, source_id: str, record: dict[str, str], vector: list[float]) -> None:
    record_hash = content_hash(record)
    source_comment_seq = parse_json_object(record["source_comment_seq"], "source_comment_seq")
    metadata = {"csv_index": record.get("index", "")}
    chunk_text = pilot.embedding_text(record)
    raw_text = json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2)

    row = connection.execute(
        """
        INSERT INTO knowledge_records (
            source_id, source_record_id, record_type, domain, title,
            raw_text, cleaned_text, problem, category, solution, resolution,
            resolution_confirmed, source_comment_seq, solution_scope,
            limitations, metadata, review_status, index_status, content_hash
        )
        VALUES (
            %s, %s, 'ticket', 'general_it', %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, 'approved', 'ready', %s
        )
        ON CONFLICT (source_id, source_record_id)
        DO UPDATE SET
            title = EXCLUDED.title,
            raw_text = EXCLUDED.raw_text,
            cleaned_text = EXCLUDED.cleaned_text,
            problem = EXCLUDED.problem,
            category = EXCLUDED.category,
            solution = EXCLUDED.solution,
            resolution = EXCLUDED.resolution,
            resolution_confirmed = EXCLUDED.resolution_confirmed,
            source_comment_seq = EXCLUDED.source_comment_seq,
            solution_scope = EXCLUDED.solution_scope,
            limitations = EXCLUDED.limitations,
            metadata = EXCLUDED.metadata,
            review_status = EXCLUDED.review_status,
            index_status = EXCLUDED.index_status,
            content_hash = EXCLUDED.content_hash,
            updated_at = now()
        RETURNING id
        """,
        (
            source_id,
            record["issueid"],
            f"Ticket {record['issueid']}",
            raw_text,
            chunk_text,
            record["problem"],
            record.get("category") or None,
            record["solution"],
            record.get("resolution") or None,
            (
                None
                if not record.get("resolution_confirmed", "").strip()
                else record["resolution_confirmed"].strip().lower() == "true"
            ),
            Jsonb(source_comment_seq),
            record.get("solution_scope") or None,
            record.get("limitations") or None,
            Jsonb(metadata),
            record_hash,
        ),
    ).fetchone()
    record_id = str(row[0])

    # Aynı kaydın eski chunk'ı veya eski embedding'i varsa temizlenir.
    connection.execute(
        "DELETE FROM knowledge_chunks WHERE record_id = %s",
        (record_id,),
    )
    connection.execute(
        """
        INSERT INTO knowledge_chunks (
            record_id, chunk_index, chunk_text, embedding,
            embedding_model, record_content_hash
        )
        VALUES (%s, 0, %s, %s, %s, %s)
        """,
        (record_id, chunk_text, vector, EMBEDDING_MODEL, record_hash),
    )


def main() -> None:
    records, csv_hash = pilot.read_tickets(pilot.CSV_PATH)
    vectors = pilot.load_cache(pilot.CACHE_PATH, records, csv_hash)
    if vectors is None:
        raise DatabaseError(
            "Embedding cache bulunamadı veya CSV ile eşleşmiyor. "
            "Önce ticket_vektor_arama.py ile 10 ticket embedding'ini oluştur."
        )

    try:
        with connect() as connection:
            source_id = upsert_source(connection)
            for record, vector in zip(records, vectors):
                upsert_record(connection, source_id, record, vector)
            record_count = connection.execute(
                "SELECT count(*) FROM knowledge_records WHERE source_id = %s",
                (source_id,),
            ).fetchone()[0]
            chunk_count = connection.execute(
                """
                SELECT count(*)
                FROM knowledge_chunks AS c
                JOIN knowledge_records AS r ON r.id = c.record_id
                WHERE r.source_id = %s
                """,
                (source_id,),
            ).fetchone()[0]
    except DatabaseError:
        raise
    except Exception as exc:
        raise DatabaseError("Pilot ticket aktarımı başarısız oldu; işlem geri alındı.") from exc

    print(f"Aktarım tamamlandı: records={record_count}, chunks={chunk_count}")
    print("Idempotency kontrolü: aynı kaynak ve issueid ile kayıt çoğaltılmaz.")


if __name__ == "__main__":
    try:
        main()
    except (DatabaseError, ValueError, pilot.PilotError) as exc:
        raise SystemExit(f"AKTARIM BAŞARISIZ: {exc}") from None
