"""Bilgi Merkezi: yönetici yüklemesi, onay ve devre dışı bırakma.

Yüklenen kayıtlar önce ``pending`` olarak girer; chunk/embedding yoktur, bu yüzden aramada görünmez.
Yönetici onayında kaydın tek chunk'ı embedding'lenir ve ``approved/ready`` olur. Kayıt silinmez;
devre dışı bırakma ``excluded`` durumudur. Dosya içeriği hiçbir zaman çalıştırılmaz.
"""
from __future__ import annotations

import csv
import io
import json
import re
from typing import Callable

from psycopg.types.json import Jsonb

import ticket_vektor_arama as vectors
from database.import_documentation import embedding_text as guide_text, validate_row
from database.import_expertise import digest
from database.import_pilot import content_hash

from kb_limits import MAX_ROWS, MAX_UPLOAD_CHARS as MAX_CONTENT_CHARS  # noqa: E402

MAX_GUIDES = 20
MAX_FIELD = 4000
MAX_EMBEDDING_TEXT = 12000
DOMAINS = ("general_it", "windows_server", "oracle_db")
SCOPES = {"", "procedure", "diagnostic_approach", "workaround", "explanation"}
REQUIRED = {"issueid", "problem", "solution"}
OPTIONAL = {"category", "resolution", "resolution_confirmed", "solution_scope", "limitations"}
SOURCE_TYPE = "admin_upload"


class KnowledgeError(ValueError):
    """Yöneticiye gösterilebilecek, ayrıntısı güvenli doğrulama hatası."""


def _clean_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w.\- ]", "_", name.strip(), flags=re.UNICODE)[:100]
    return cleaned or "dosya"


def parse_tickets_csv(content: str, domain: str) -> tuple[list[dict], list[str]]:
    """CSV metnini doğrular; (kayıtlar, hata listesi) döndürür. Hata varsa kayıt listesi güvenilmez."""
    if domain not in DOMAINS:
        raise KnowledgeError("Alan geçersiz.")
    errors: list[str] = []
    reader = csv.DictReader(io.StringIO(content.lstrip("﻿"), newline=""))
    fields = set(reader.fieldnames or [])
    if not REQUIRED <= fields:
        raise KnowledgeError("CSV'de eksik sütunlar var: " + ", ".join(sorted(REQUIRED - fields)))
    if fields - REQUIRED - OPTIONAL:
        raise KnowledgeError("CSV'de tanınmayan sütunlar var: " + ", ".join(sorted(fields - REQUIRED - OPTIONAL)))
    records, seen = [], set()
    for number, row in enumerate(reader, start=2):
        if len(records) >= MAX_ROWS:
            raise KnowledgeError(f"Bir yüklemede en fazla {MAX_ROWS} kayıt olabilir.")
        if None in row or any(value is None for value in row.values()):
            errors.append(f"Satır {number}: sütun sayısı tutarsız.")
            continue
        record = {key: value.strip() for key, value in row.items()}
        problems = []
        if any(not record[key] for key in REQUIRED):
            problems.append("issueid, problem ve solution boş olamaz")
        if len(record["issueid"]) > 100:
            problems.append("issueid 100 karakteri aşamaz")
        if len(record["problem"]) > MAX_FIELD or len(record["solution"]) > MAX_FIELD:
            problems.append(f"problem ve solution en fazla {MAX_FIELD} karakter olabilir")
        if record.get("solution_scope", "") not in SCOPES:
            problems.append("solution_scope geçersiz")
        if record.get("resolution_confirmed", "").lower() not in {"", "true", "false"}:
            problems.append("resolution_confirmed true, false veya boş olmalı")
        if record["issueid"] in seen:
            problems.append("yinelenen issueid")
        if problems:
            errors.append(f"Satır {number}: " + "; ".join(problems) + ".")
            continue
        seen.add(record["issueid"])
        records.append(record)
    if not records and not errors:
        raise KnowledgeError("CSV'de kayıt yok.")
    return records, errors


def parse_guides_json(content: str) -> tuple[list[dict], list[str]]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise KnowledgeError("JSON geçerli değil.") from None
    items = data if isinstance(data, list) else [data]
    if not 1 <= len(items) <= MAX_GUIDES:
        raise KnowledgeError(f"Bir yüklemede 1-{MAX_GUIDES} rehber olabilir.")
    records, errors, seen = [], [], set()
    for number, item in enumerate(items, start=1):
        try:
            row = validate_row(item)
            if row["source_record_id"] in seen:
                raise ValueError("yinelenen source_record_id")
            seen.add(row["source_record_id"])
            records.append(row)
        except ValueError as error:
            errors.append(f"Rehber {number}: {error}")
    return records, errors


def preview_items(kind: str, records: list[dict], domain: str, limit: int = 10) -> list[dict]:
    return [{"id": r.get("issueid") or r["source_record_id"], "domain": r.get("domain", domain),
             "title": r.get("title") or f"Ticket {r['issueid']}", "problem": r["problem"][:200]}
            for r in records[:limit]]


def _upsert_source(connection, name: str, version: str, license_note: str, url: str | None = None) -> str:
    row = connection.execute(
        "INSERT INTO knowledge_sources (name, source_type, source_url, license, source_version) "
        "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (name, source_version) "
        "DO UPDATE SET license = EXCLUDED.license RETURNING id",
        (name, SOURCE_TYPE, url, license_note, version)).fetchone()
    return str(row[0])


def stage_tickets(connection, records: list[dict], *, domain: str, filename: str,
                  license_note: str, file_digest: str) -> dict:
    source_id = _upsert_source(connection, f"Admin yüklemesi: {_clean_filename(filename)}",
                               f"tickets-{file_digest[:16]}", license_note)
    added = present = 0
    for record in records:
        text = vectors.embedding_text(record)
        if len(text) > MAX_EMBEDDING_TEXT:
            raise KnowledgeError(f"{record['issueid']}: kayıt metni çok uzun.")
        keyed = {**record, "domain": domain}
        confirmed = record.get("resolution_confirmed", "").lower()
        row = connection.execute(
            "INSERT INTO knowledge_records (source_id, source_record_id, record_type, domain, title, "
            "raw_text, cleaned_text, problem, category, solution, resolution, resolution_confirmed, "
            "solution_scope, limitations, metadata, review_status, index_status, content_hash) "
            "VALUES (%s, %s, 'ticket', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', 'pending', %s) "
            "ON CONFLICT (source_id, source_record_id) DO NOTHING RETURNING id",
            (source_id, record["issueid"], domain, f"Ticket {record['issueid']}",
             json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2), text, record["problem"],
             record.get("category") or None, record["solution"], record.get("resolution") or None,
             None if not confirmed else confirmed == "true", record.get("solution_scope") or None,
             record.get("limitations") or None, Jsonb({"uploaded_via": "admin_panel"}),
             content_hash(keyed))).fetchone()
        added += 1 if row else 0
        present += 0 if row else 1
    return {"added": added, "already_present": present}


def stage_guides(connection, records: list[dict], *, filename: str, file_digest: str) -> dict:
    added = present = 0
    for row in records:
        text = guide_text(row)
        source_id = _upsert_source(connection, row["source_name"], row["source_version"], row["license"],
                                   row["source_url"])
        metadata = dict(row)
        metadata["official_sources"] = [{"title": row["title"], "url": row["source_url"]}]
        metadata["uploaded_via"] = "admin_panel"
        found = connection.execute(
            "INSERT INTO knowledge_records (source_id, source_record_id, record_type, domain, title, "
            "raw_text, cleaned_text, problem, solution, resolution, resolution_confirmed, solution_scope, "
            "limitations, metadata, review_status, index_status, content_hash) "
            "VALUES (%s, %s, 'documentation', %s, %s, NULL, %s, %s, %s, %s, NULL, 'procedure', %s, %s, "
            "'pending', 'pending', %s) ON CONFLICT (source_id, source_record_id) DO NOTHING RETURNING id",
            (source_id, row["source_record_id"], row["domain"], row["title"], text, row["problem"],
             row["solution"], row["resolution"], row["limitations"], Jsonb(metadata), digest(row))).fetchone()
        added += 1 if found else 0
        present += 0 if found else 1
    return {"added": added, "already_present": present}


def approve_record(connection, record_id: str, embed: Callable[[str], list[float]]) -> dict:
    """Tek kaydı indeksler ve onaylar. Aynı işlem ``connection`` üzerinde; commit çağırana aittir."""
    row = connection.execute(
        "SELECT cleaned_text, content_hash, review_status, index_status FROM knowledge_records "
        "WHERE id = %s FOR UPDATE", (record_id,)).fetchone()
    if row is None:
        raise KnowledgeError("Kayıt bulunamadı.")
    text, record_hash, review, index = row
    if review == "approved" and index == "ready":
        return {"status": "already"}
    chunk = connection.execute(
        "SELECT 1 FROM knowledge_chunks WHERE record_id = %s AND chunk_index = 0 "
        "AND record_content_hash = %s AND embedding_model = %s",
        (record_id, record_hash, vectors.MODEL)).fetchone()
    if chunk is None:
        if not text or len(text) > MAX_EMBEDDING_TEXT:
            raise KnowledgeError("Kayıt metni boş veya çok uzun.")
        vector = vectors.normalized_vector(embed(text))
        connection.execute("DELETE FROM knowledge_chunks WHERE record_id = %s", (record_id,))
        connection.execute(
            "INSERT INTO knowledge_chunks (record_id, chunk_index, chunk_text, embedding, embedding_model, "
            "record_content_hash) VALUES (%s, 0, %s, %s, %s, %s)",
            (record_id, text, vector, vectors.MODEL, record_hash))
    connection.execute(
        "UPDATE knowledge_records SET review_status = 'approved', index_status = 'ready', updated_at = now() "
        "WHERE id = %s", (record_id,))
    return {"status": "indexed"}


def exclude_record(connection, record_id: str, excluded: bool) -> dict:
    """Kaydı aramadan çıkarır veya geri alır; chunk silinmez. Geri alma yalnız geçerli chunk varsa onaylar."""
    row = connection.execute(
        "SELECT content_hash FROM knowledge_records WHERE id = %s FOR UPDATE", (record_id,)).fetchone()
    if row is None:
        raise KnowledgeError("Kayıt bulunamadı.")
    if excluded:
        connection.execute("UPDATE knowledge_records SET review_status = 'excluded', updated_at = now() "
                           "WHERE id = %s", (record_id,))
        return {"status": "excluded"}
    chunk = connection.execute(
        "SELECT 1 FROM knowledge_chunks WHERE record_id = %s AND record_content_hash = %s AND embedding_model = %s",
        (record_id, row[0], vectors.MODEL)).fetchone()
    status = "approved" if chunk else "pending"
    connection.execute(
        "UPDATE knowledge_records SET review_status = %s, index_status = %s, updated_at = now() WHERE id = %s",
        (status, "ready" if chunk else "pending", record_id))
    return {"status": status}


def summary(connection) -> dict:
    rows = connection.execute(
        "SELECT record_type, domain, review_status, count(*) FROM knowledge_records "
        "GROUP BY record_type, domain, review_status ORDER BY 1, 2, 3").fetchall()
    chunks = connection.execute("SELECT count(*) FROM knowledge_chunks").fetchone()[0]
    return {"groups": [{"record_type": a, "domain": b, "review_status": c, "count": n} for a, b, c, n in rows],
            "total": sum(n for *_, n in rows), "searchable": connection.execute(
                "SELECT count(*) FROM knowledge_records r WHERE r.review_status = 'approved' "
                "AND r.index_status = 'ready' AND EXISTS (SELECT 1 FROM knowledge_chunks c "
                "WHERE c.record_id = r.id AND c.record_content_hash = r.content_hash)").fetchone()[0],
            "chunks": chunks}


def list_records(connection, *, review_status: str | None = None, domain: str | None = None,
                 record_type: str | None = None, query: str | None = None,
                 offset: int = 0, limit: int = 50) -> dict:
    if review_status not in (None, "pending", "approved", "excluded") or domain not in (None, *DOMAINS) \
            or record_type not in (None, "ticket", "qa", "documentation"):
        raise KnowledgeError("Süzgeç değeri geçersiz.")
    if not (0 <= offset <= 1_000_000 and 1 <= limit <= 100):
        raise KnowledgeError("Sayfa değerleri geçersiz.")
    pattern = None
    if query:
        pattern = "%" + re.sub(r"([\\%_])", r"\\\1", query.strip()[:100]) + "%"
    where = ("WHERE (%s::text IS NULL OR r.review_status = %s) AND (%s::text IS NULL OR r.domain = %s) "
             "AND (%s::text IS NULL OR r.record_type = %s) AND (%s::text IS NULL OR r.source_record_id ILIKE %s "
             "OR r.title ILIKE %s OR r.problem ILIKE %s)")
    args = (review_status, review_status, domain, domain, record_type, record_type,
            pattern, pattern, pattern, pattern)
    total = connection.execute("SELECT count(*) FROM knowledge_records r " + where, args).fetchone()[0]
    rows = connection.execute(
        "SELECT r.id, r.source_record_id, r.record_type, r.domain, r.title, r.review_status, r.index_status, "
        "s.name, s.license, r.created_at, left(r.problem, 200) FROM knowledge_records r "
        "JOIN knowledge_sources s ON s.id = r.source_id " + where +
        " ORDER BY r.created_at DESC, r.source_record_id LIMIT %s OFFSET %s", args + (limit + 1, offset)).fetchall()
    items = [{"id": str(a), "source_record_id": b, "record_type": c, "domain": d, "title": e or "",
              "review_status": f, "index_status": g, "source_name": h, "license": i or "",
              "created_at": j, "problem": k} for a, b, c, d, e, f, g, h, i, j, k in rows[:limit]]
    return {"items": items, "total": total, "next_offset": offset + limit if len(rows) > limit else None}
