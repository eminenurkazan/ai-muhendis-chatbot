"""İncelenmiş soru-cevapları mevcut Cloudflare embedding ve pgvector ile aktarır."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from psycopg.types.json import Jsonb

import ticket_vektor_arama as vectors
from .connection import DatabaseError, connect


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def load_records(path: Path, *, allow_unverified: bool = False) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data.get("records")
    if data.get("format_version") != 1 or not isinstance(records, list) or not 1 <= len(records) <= 100:
        raise ValueError("Aktarım dosyası format_version=1 ve 1–100 kayıt içermeli.")
    seen = set()
    for row in records:
        original = row.get("original_source", {})
        site = {"windows_server": "serverfault", "oracle_db": "dba"}.get(row.get("domain"))
        expected = f"{site}:q{original.get('question_id')}:a{original.get('answer_id')}"
        if site is None or row.get("source_record_id") != expected or expected in seen:
            raise ValueError("Kaynak kimliği, alanı veya soru-cevap eşleştirmesi geçersiz.")
        seen.add(expected)
        if original.get("source_record_id") != expected or original.get("domain") != row["domain"]:
            raise ValueError("Özgün kayıt ile aktarım kaydı eşleşmiyor.")
        source_only = (allow_unverified
                       and row.get("official_verification_status") == "not_checked"
                       and row.get("user_authorized_source_review_import") is True
                       and row.get("official_sources") == []
                       and "not_checked" in row.get("official_context", ""))
        if (row.get("review_decision") != "uygun_sinirli_kapsam"
                or (row.get("official_verification_status") != "partially_supported_scoped" and not source_only)
                or row.get("resolution_confirmed", "missing") is not None
                or original.get("answer_accepted") is not True):
            raise ValueError("Sınırlı kapsam incelemesi veya null doğrulama alanı eksik.")
        for key in ("title", "problem", "solution", "resolution", "limitations", "source_name", "source_version"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f"Gerekli aktarım alanı eksik: {key}")
        if row.get("solution_scope") not in {"explanation", "diagnostic_approach"}:
            raise ValueError("Bu aktarım yalnız açıklama/teşhis kayıtlarını kabul eder.")
        for key in ("source_url", "answer_url", "question_license", "answer_license", "question_license_url", "answer_license_url"):
            if not row.get(key) or row[key] != original.get(key):
                raise ValueError(f"Kaynak atfı korunmamış: {key}")
        host = "serverfault.com" if site == "serverfault" else "dba.stackexchange.com"
        if not row["source_url"].startswith(f"https://{host}/questions/{original['question_id']}/") or row["answer_url"] != f"https://{host}/a/{original['answer_id']}":
            raise ValueError("Kaynak URL’si kimlikle uyuşmuyor.")
        for key in ("question_author", "answer_author"):
            author = row.get(key, {})
            if not author.get("name") or not author.get("url") or author != original.get(key):
                raise ValueError("Soru/cevap yazar atfı eksik.")
        if (not row.get("official_sources") and not source_only) or not row.get("source_evidence"):
            raise ValueError("Resmî belge ve kaynak kanıtı gerekli.")
        for evidence in row["source_evidence"]:
            if evidence.get("field") not in {"problem", "solution"} or not evidence.get("quote") or evidence["quote"] not in original[evidence["field"]]:
                raise ValueError("Kanıt alıntısı özgün kaynakta bulunamadı.")
        if "```" in row["solution"] or row.get("whole_answer_approved") is not False:
            raise ValueError("Ham cevap veya kod bloğu bu kapsamda indekslenemez.")
    return records


def embedding_text(row: dict) -> str:
    return (f"Title: {row['title']}\nDomain: {row['domain']}\n"
            f"Problem: {row['problem']}\nReviewed source answer: {row['solution']}\n"
            f"Product/environment: {row['product_version_environment']}\n"
            f"Official verification note (separate from community answer): {row['official_context']}\n"
            f"Outcome: {row['resolution']}\nScope: {row['solution_scope']}\n"
            f"Limitations: {row['limitations']}")


def load_vectors(path: Path, records: list[dict]) -> list[list[float]] | None:
    if not path.exists():
        return None
    cache = json.loads(path.read_text(encoding="utf-8"))
    if (cache.get("model") != vectors.MODEL or cache.get("dimensions") != vectors.DIMENSION
            or cache.get("record_hashes") != [digest(r) for r in records]
            or cache.get("text_hashes") != [digest(embedding_text(r)) for r in records]):
        raise ValueError("Embedding önbelleği bu veri/sürümle uyuşmuyor; farklı bir cache yolu seç.")
    rows = cache.get("vectors", [])
    if len(rows) != len(records):
        raise ValueError("Embedding sayısı kayıt sayısıyla uyuşmuyor.")
    return [vectors.normalized_vector(v) for v in rows]


def embed(records: list[dict], cache_path: Path) -> None:
    if load_vectors(cache_path, records) is not None:
        print(f"Embedding önbelleği hazır: {len(records)} kayıt.")
        return
    import rag_ticket_pilotu as rag
    if not rag.cloudflare_credentials_path().exists():
        raise ValueError("Kayıtlı Cloudflare erişimi bulunamadı; mevcut giriş akışını tamamla.")
    account, token, _ = rag.cloudflare_credentials()
    try:
        embeddings = vectors.cloud_embeddings(account, token, [embedding_text(r) for r in records])
    finally:
        del token
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("x", encoding="utf-8") as handle:
        json.dump({"format_version": 1, "model": vectors.MODEL, "dimensions": vectors.DIMENSION,
                   "record_hashes": [digest(r) for r in records],
                   "text_hashes": [digest(embedding_text(r)) for r in records], "vectors": embeddings}, handle, ensure_ascii=False, allow_nan=False)
    print(f"Embedding üretildi: {len(embeddings)} kayıt, {vectors.DIMENSION} boyut.")


def ticket_snapshot(connection) -> dict:
    records = connection.execute("""SELECT count(*),md5(coalesce(string_agg(to_jsonb(r)::text,'|' ORDER BY r.id),''))
        FROM knowledge_records r WHERE r.record_type='ticket'""").fetchone()
    chunks = connection.execute("""SELECT count(*),md5(coalesce(string_agg(to_jsonb(c)::text,'|' ORDER BY c.id),''))
        FROM knowledge_chunks c JOIN knowledge_records r ON r.id=c.record_id WHERE r.record_type='ticket'""").fetchone()
    return {"record_count": records[0], "record_hash": records[1], "chunk_count": chunks[0], "chunk_hash": chunks[1]}


def import_records(records: list[dict], cache_path: Path) -> dict:
    embeddings = load_vectors(cache_path, records)
    if embeddings is None:
        raise ValueError("Önce embed adımını çalıştır.")
    with connect() as connection:
        connection.execute("SELECT pg_advisory_xact_lock(191198006)")
        before = ticket_snapshot(connection)
        added = skipped = 0
        for row, embedding in zip(records, embeddings, strict=True):
            site_url = "https://serverfault.com" if row["domain"] == "windows_server" else "https://dba.stackexchange.com"
            connection.execute("""INSERT INTO knowledge_sources (name,source_type,source_version,source_url)
                VALUES (%s,'community_qa',%s,%s) ON CONFLICT (name,source_version) DO NOTHING""",
                (row["source_name"], row["source_version"], site_url))
            source_id = connection.execute("SELECT id FROM knowledge_sources WHERE name=%s AND source_version=%s",
                (row["source_name"], row["source_version"])).fetchone()[0]
            existing = connection.execute("SELECT id,source_id,content_hash FROM knowledge_records WHERE source_record_id=%s",
                (row["source_record_id"],)).fetchall()
            record_hash = digest(row)
            if existing:
                if len(existing) != 1 or existing[0][1] != source_id or existing[0][2] != record_hash:
                    raise ValueError("Mevcut kimlik farklı içerikle kayıtlı; üzerine yazılmadı.")
                skipped += 1
                continue
            metadata = {key: value for key, value in row.items() if key not in {"original_source", "problem", "solution", "resolution"}}
            metadata["question_url"] = row["source_url"]
            text = embedding_text(row)
            rid = connection.execute("""INSERT INTO knowledge_records (
                source_id,source_record_id,record_type,domain,title,raw_text,cleaned_text,problem,category,
                solution,resolution,resolution_confirmed,source_comment_seq,solution_scope,limitations,metadata,
                review_status,index_status,content_hash)
                VALUES (%s,%s,'qa',%s,%s,%s,%s,%s,%s,%s,%s,NULL,NULL,%s,%s,%s,'approved','ready',%s) RETURNING id""",
                (source_id,row["source_record_id"],row["domain"],row["title"],json.dumps(row["original_source"],ensure_ascii=False),
                 text,row["problem"],row["domain"],row["solution"],row["resolution"],row["solution_scope"],row["limitations"],Jsonb(metadata),record_hash)).fetchone()[0]
            connection.execute("""INSERT INTO knowledge_chunks
                (record_id,chunk_index,chunk_text,embedding,embedding_model,record_content_hash)
                VALUES (%s,0,%s,%s,%s,%s)""", (rid,text,embedding,vectors.MODEL,record_hash))
            added += 1
        after = ticket_snapshot(connection)
        if before != after:
            raise ValueError("Mevcut ticketlar değişti; aktarım geri alındı.")
    return {"added":added,"already_present":skipped,"existing_tickets_unchanged":before}


def verify(records: list[dict], cache_path: Path) -> dict:
    embeddings = load_vectors(cache_path, records)
    if embeddings is None:
        raise ValueError("Embedding önbelleği yok.")
    from .search import search_chunks
    checked = []
    with connect() as connection:
        for row in records:
            found = connection.execute("""SELECT r.record_type,r.domain,r.review_status,r.index_status,r.resolution_confirmed,
                r.content_hash,c.chunk_text,vector_dims(c.embedding),c.embedding_model,c.record_content_hash,r.metadata
                FROM knowledge_records r JOIN knowledge_chunks c ON c.record_id=r.id
                WHERE r.source_record_id=%s""", (row["source_record_id"],)).fetchall()
            if len(found) != 1:
                raise ValueError("Aktarılan kayıt için tam bir chunk bulunamadı.")
            f=found[0]
            if f[:6] != ('qa',row['domain'],'approved','ready',None,digest(row)) or f[6] != embedding_text(row) or f[7:10] != (vectors.DIMENSION,vectors.MODEL,digest(row)):
                raise ValueError("Aktarılan kayıt/embedding doğrulaması başarısız.")
            if f[10]['question_author'] != row['question_author'] or f[10]['answer_license'] != row['answer_license']:
                raise ValueError("Veritabanı kaynak atfı eşleşmiyor.")
        counts=connection.execute("SELECT record_type,domain,count(*) FROM knowledge_records WHERE review_status='approved' AND index_status='ready' GROUP BY 1,2 ORDER BY 1,2").fetchall()
    for row, vector in zip(records,embeddings,strict=True):
        hits=search_chunks(vector,embedding_model=vectors.MODEL,domains=('general_it',row['domain']))
        if row['source_record_id'] not in [r['issueid'] for _,r in hits]:
            raise ValueError("Yeni kayıt kendi vektörüyle ilk üçte bulunamadı.")
        checked.append(row['source_record_id'])
    return {"checked":checked,"approved_ready_counts":counts,"self_vector_top3":"passed (hazırlık kontrolü; doğal dil başarımı değildir)"}


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['check','embed','import','verify'])
    parser.add_argument('--records',type=Path,required=True)
    parser.add_argument('--cache',type=Path)
    parser.add_argument("--allow-unverified", action="store_true", help="Kullanıcının açık onayıyla kaynak incelemesi yapılmış, resmî kontrolsüz kayıtları aktarır.")
    args=parser.parse_args()
    records=load_records(args.records, allow_unverified=args.allow_unverified)
    cache=args.cache or args.records.with_suffix('.embeddings.json')
    if args.action=='check': result={'checked':len(records),'ids':[r['source_record_id'] for r in records]}
    elif args.action=='embed': embed(records,cache); return
    elif args.action=='import': result=import_records(records,cache)
    else: result=verify(records,cache)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    try:
        main()
    except (ValueError,OSError,DatabaseError,vectors.PilotError) as exc:
        raise SystemExit(f'AKTARIM TAMAMLANMADI: {exc}') from None
