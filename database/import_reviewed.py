"""Kontrol edilmiş ek ticketları vektörleştirir ve PostgreSQL'e aktarır.

Proje kökünde sırasıyla çalıştır:
    python -m database.import_reviewed check
    python -m database.import_reviewed embed
    python -m database.import_reviewed import

Kısa ticketlarda problem ve çözüm aynı arama parçasında tutulur.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import ticket_vektor_arama as vectors
from .connection import DatabaseError, connect
from .import_pilot import upsert_record


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "tickets_reviewed_extra.csv"
RAW_PATH = ROOT / "sample_utterances.csv"
CACHE_PATH = ROOT / "outputs_local" / "ticket_vektorleri_extra.json"
SOURCE_NAME = "Mendeley Service Desk Tickets"
SOURCE_TYPE = "ticket_dataset"
SOURCE_VERSION = "reviewed-2026-10-09"
EXPECTED_COLUMNS = {
    "issueid", "problem", "category", "solution", "resolution",
    "resolution_confirmed", "source_comment_seq", "solution_scope", "limitations",
}
SCOPES = {"procedure", "diagnostic_approach", "workaround", "explanation"}


def source_comments() -> dict[str, set[int]]:
    available: dict[str, set[int]] = defaultdict(set)
    with RAW_PATH.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            available[row["issueid"]].add(int(float(row["comment_seq"])))
    return available


def checked_records() -> tuple[list[dict[str, str]], str]:
    records, csv_hash = vectors.read_tickets(CSV_PATH)
    old_records, _ = vectors.read_tickets(vectors.CSV_PATH)
    old_ids = {record["issueid"] for record in old_records}
    available = source_comments()
    seen: set[str] = set()

    for record in records:
        issueid = record["issueid"]
        if set(record) != EXPECTED_COLUMNS:
            raise ValueError(f"{issueid}: CSV sütunları beklenen biçimde değil.")
        if issueid in seen or issueid in old_ids:
            raise ValueError(f"{issueid}: yinelenen ticket kimliği.")
        seen.add(issueid)
        if record["resolution_confirmed"] not in {"true", "false"}:
            raise ValueError(f"{issueid}: resolution_confirmed true veya false olmalı.")
        if record["solution_scope"] not in SCOPES:
            raise ValueError(f"{issueid}: solution_scope geçersiz.")
        if not record["resolution"] or not record["limitations"]:
            raise ValueError(f"{issueid}: sonuç ve sınırlamalar boş olamaz.")
        try:
            references = json.loads(record["source_comment_seq"])
        except json.JSONDecodeError as exc:
            raise ValueError(f"{issueid}: yorum numaraları geçerli JSON değil.") from exc
        if not isinstance(references, dict) or set(references) != {"problem", "solution", "resolution"}:
            raise ValueError(f"{issueid}: problem, solution ve resolution yorumları gerekli.")
        for field, numbers in references.items():
            if (not isinstance(numbers, list) or not numbers
                    or any(type(number) is not int or number not in available.get(issueid, set())
                           for number in numbers)):
                raise ValueError(f"{issueid}: {field} için kaynak yorum numarası bulunamadı.")

    return records, csv_hash


def embed(records: list[dict[str, str]], csv_hash: str) -> None:
    cached = vectors.load_cache(CACHE_PATH, records, csv_hash)
    if cached is not None:
        print(f"Embedding önbelleği hazır: {len(cached)} kayıt.")
        return

    import rag_ticket_pilotu as rag

    try:
        account_id, token, is_new = rag.cloudflare_credentials()
    except rag.RagError as exc:
        raise ValueError(str(exc)) from None
    try:
        texts = [vectors.embedding_text(record) for record in records]
        new_vectors = vectors.cloud_embeddings(account_id, token, texts)
        if is_new:
            rag.save_cloudflare_credentials(account_id, token)
        vectors.save_cache(CACHE_PATH, records, csv_hash, new_vectors)
    except vectors.PilotError as exc:
        if str(exc).startswith("HTTP 401:"):
            rag.forget_cloudflare_credentials()
        raise
    except rag.RagError as exc:
        raise ValueError(str(exc)) from None
    finally:
        del token
    print(f"Embedding üretildi: {len(new_vectors)} kayıt, {vectors.DIMENSION} boyut.")


def upsert_source(connection) -> str:
    row = connection.execute(
        """
        INSERT INTO knowledge_sources (name, source_type, source_version)
        VALUES (%s, %s, %s)
        ON CONFLICT (name, source_version)
        DO UPDATE SET source_type = EXCLUDED.source_type
        RETURNING id
        """,
        (SOURCE_NAME, SOURCE_TYPE, SOURCE_VERSION),
    ).fetchone()
    return str(row[0])


def import_records(records: list[dict[str, str]], csv_hash: str) -> None:
    cached = vectors.load_cache(CACHE_PATH, records, csv_hash)
    if cached is None:
        raise DatabaseError("Embedding önbelleği eksik veya CSV değişmiş. Önce embed adımını çalıştır.")
    try:
        with connect() as connection:
            source_id = upsert_source(connection)
            for record, vector in zip(records, cached, strict=True):
                upsert_record(connection, source_id, record, vector)
            count = connection.execute(
                "SELECT count(*) FROM knowledge_records WHERE source_id = %s",
                (source_id,),
            ).fetchone()[0]
    except DatabaseError:
        raise
    except Exception as exc:
        raise DatabaseError("Ek ticket aktarımı tamamlanamadı; işlem geri alındı.") from exc
    print(f"Veritabanına aktarıldı: {count} ek kayıt.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "embed", "import"))
    action = parser.parse_args().action
    records, csv_hash = checked_records()
    print(f"Kontrol edildi: {len(records)} ek ticket; kaynak yorum numaraları geçerli.")
    if action == "embed":
        embed(records, csv_hash)
    elif action == "import":
        import_records(records, csv_hash)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, DatabaseError, vectors.PilotError) as exc:
        raise SystemExit(f"İŞLEM TAMAMLANMADI: {exc}") from None
