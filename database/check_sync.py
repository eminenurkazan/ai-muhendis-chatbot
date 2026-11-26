"""Bilgi tabanında kayıt–vektör tutarlılığını ve MSSQL atıflarını denetler (salt okunur).

Kullanım:
    python -m database.check_sync            # PostgreSQL kayıt/chunk kontrolleri
    python -m database.check_sync --mssql    # ek olarak sohbet atıflarının PostgreSQL'de bulunması
    python -m database.check_sync --json     # makine okunur çıktı

Hiçbir kaydı değiştirmez. "hata" düzeyinde bulgu varsa çıkış kodu 1'dir.
Arama, yalnız approved/ready, aynı modelli ve hash'i kayıtla eşleşen chunk'ları kullandığı için
bu bulgular yanlış yanıta değil, kaydın aramadan sessizce düşmesine yol açar; kontrolün amacı
bu sessiz kopuklukları görünür kılmaktır.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
import sys

from .connection import DatabaseError, connect

EMBEDDING_MODEL = "@cf/baai/bge-m3"
EMBEDDING_DIMENSION = 1024
SAMPLE_LIMIT = 20

SEARCHABLE = """
    r.review_status = 'approved' AND r.index_status = 'ready'
    AND EXISTS (SELECT 1 FROM knowledge_chunks c WHERE c.record_id = r.id
                AND c.record_content_hash = r.content_hash AND c.embedding_model = %(model)s)
"""


@dataclass(frozen=True)
class Check:
    key: str
    level: str  # "hata" veya "bilgi"
    title: str
    explanation: str
    sql: str  # İlk sütun gösterilecek kayıt kimliği olmalı.


CHECKS = (
    Check("ready_without_chunk", "hata",
          "Onaylı/hazır ama hiç chunk'ı olmayan kayıt",
          "Kayıt aranabilir görünüyor ama vektörü yok; hiçbir aramada çıkmaz.",
          """SELECT r.source_record_id FROM knowledge_records r
             WHERE r.review_status = 'approved' AND r.index_status = 'ready'
               AND NOT EXISTS (SELECT 1 FROM knowledge_chunks c WHERE c.record_id = r.id)
             ORDER BY 1"""),
    Check("stale_vector", "hata",
          "Vektörü kaydın güncel içeriğiyle eşleşmeyen kayıt",
          "Kayıt metni değişmiş, vektör eski metinden kalmış; arama bu kaydı kullanmaz.",
          """SELECT r.source_record_id FROM knowledge_records r
             WHERE r.review_status = 'approved' AND r.index_status = 'ready'
               AND EXISTS (SELECT 1 FROM knowledge_chunks c WHERE c.record_id = r.id)
               AND NOT EXISTS (SELECT 1 FROM knowledge_chunks c WHERE c.record_id = r.id
                               AND c.record_content_hash = r.content_hash)
             ORDER BY 1"""),
    Check("foreign_model", "hata",
          "Beklenen embedding modelinden veya boyutundan farklı vektör",
          f"Arama yalnız {EMBEDDING_MODEL} ({EMBEDDING_DIMENSION} boyut) vektörlerini karşılaştırır.",
          """SELECT DISTINCT r.source_record_id FROM knowledge_chunks c
             JOIN knowledge_records r ON r.id = c.record_id
             WHERE c.embedding_model <> %(model)s OR vector_dims(c.embedding) <> %(dimension)s
             ORDER BY 1"""),
    Check("chunk_index_gap", "hata",
          "chunk_index değerleri 0'dan başlayıp ardışık gitmeyen kayıt",
          "Çoklu chunk'lı bir kayıtta eksik parça var demektir.",
          """SELECT r.source_record_id FROM knowledge_chunks c
             JOIN knowledge_records r ON r.id = c.record_id
             GROUP BY r.id, r.source_record_id
             HAVING min(c.chunk_index) <> 0 OR max(c.chunk_index) <> count(*) - 1
             ORDER BY 1"""),
    Check("ready_not_approved", "hata",
          "index_status=ready ama review_status onaylı değil (excluded hariç)",
          "Onay akışının dışında indekslenmiş kayıt; durum alanları birbiriyle çelişiyor.",
          """SELECT r.source_record_id FROM knowledge_records r
             WHERE r.index_status = 'ready' AND r.review_status = 'pending'
             ORDER BY 1"""),
    Check("approved_not_ready", "bilgi",
          "Onaylı ama indeksi hazır olmayan kayıt (pending/error)",
          "Embedding üretimi bekliyor veya başarısız olmuş; Bilgi Merkezi'nden yeniden indekslenebilir.",
          """SELECT r.source_record_id FROM knowledge_records r
             WHERE r.review_status = 'approved' AND r.index_status <> 'ready'
             ORDER BY 1"""),
    Check("excluded_with_chunk", "bilgi",
          "Devre dışı bırakılmış ama chunk'ı duran kayıt",
          "Beklenen durum: devre dışı bırakma chunk'ı silmez, geri alındığında yeniden kullanılır. Aramaya girmez.",
          """SELECT DISTINCT r.source_record_id FROM knowledge_records r
             JOIN knowledge_chunks c ON c.record_id = r.id
             WHERE r.review_status = 'excluded'
             ORDER BY 1"""),
)


@dataclass
class Finding:
    key: str
    level: str
    title: str
    explanation: str
    count: int
    sample: list[str] = field(default_factory=list)


def run_checks(connection) -> dict:
    params = {"model": EMBEDDING_MODEL, "dimension": EMBEDDING_DIMENSION}
    findings = []
    for check in CHECKS:
        ids = [str(row[0]) for row in connection.execute(check.sql, params).fetchall()]
        findings.append(Finding(check.key, check.level, check.title, check.explanation, len(ids), ids[:SAMPLE_LIMIT]))
    records, chunks = connection.execute(
        "SELECT (SELECT count(*) FROM knowledge_records), (SELECT count(*) FROM knowledge_chunks)").fetchone()
    approved_ready = connection.execute(
        "SELECT count(*) FROM knowledge_records WHERE review_status = 'approved' AND index_status = 'ready'"
    ).fetchone()[0]
    searchable = connection.execute(
        "SELECT count(*) FROM knowledge_records r WHERE " + SEARCHABLE, params).fetchone()[0]
    return {"records": records, "chunks": chunks, "approved_ready": approved_ready,
            "searchable": searchable, "findings": findings}


def cited_source_ids(mssql_connection) -> list[str]:
    """MSSQL'deki asistan yanıtlarının atıf yaptığı kaynak kimlikleri (tekil)."""
    rows = mssql_connection.cursor().execute(
        "SELECT DISTINCT j.value FROM dbo.chat_messages m "
        "CROSS APPLY OPENJSON(m.citations_json) j "
        "WHERE m.role = N'assistant' AND m.citations_json IS NOT NULL AND ISJSON(m.citations_json) = 1"
    ).fetchall()
    return sorted(str(row[0]) for row in rows)


def check_citations(connection, cited: list[str]) -> Finding:
    """Atıf yapılan kaynaklar PostgreSQL'de hâlâ aranabilir mi?"""
    missing: list[str] = []
    if cited:
        found = {str(row[0]) for row in connection.execute(
            "SELECT r.source_record_id FROM knowledge_records r WHERE r.source_record_id = ANY(%(ids)s) AND "
            + SEARCHABLE, {"ids": cited, "model": EMBEDDING_MODEL}).fetchall()}
        missing = [item for item in cited if item not in found]
    return Finding(
        "citation_not_searchable", "bilgi",
        "Sohbet yanıtlarında atıf yapılmış ama artık aranamayan kaynak",
        "Eski yanıtların kaynak görüntüsü MSSQL'de korunur; kayıt silinmiş, devre dışı bırakılmış veya "
        "vektörü bayatlamış olabilir.",
        len(missing), missing[:SAMPLE_LIMIT])


def has_errors(report: dict) -> bool:
    return any(f.level == "hata" and f.count for f in report["findings"])


def format_report(report: dict) -> str:
    lines = [
        "Bilgi tabanı senkronizasyon kontrolü (salt okunur)",
        f"Kayıt: {report['records']} · Chunk: {report['chunks']} · Onaylı/hazır: {report['approved_ready']} "
        f"· Aranabilir: {report['searchable']}",
    ]
    if "cited_sources" in report:
        lines.append(f"MSSQL'de atıf yapılan tekil kaynak: {report['cited_sources']}")
    lines.append("")
    for finding in report["findings"]:
        mark = "TAMAM" if finding.count == 0 else ("HATA " if finding.level == "hata" else "BİLGİ")
        lines.append(f"[{mark}] {finding.title}: {finding.count}")
        if finding.count:
            lines.append(f"        {finding.explanation}")
            more = f" (+{finding.count - len(finding.sample)} daha)" if finding.count > len(finding.sample) else ""
            lines.append(f"        Örnek: {', '.join(finding.sample)}{more}")
    lines.append("")
    if has_errors(report):
        lines.append("SONUÇ: Tutarsızlık var. Hata satırlarındaki kayıtlar aramada kullanılmıyor.")
    else:
        lines.append(f"SONUÇ: Tutarlı. Onaylı/hazır {report['approved_ready']} kaydın "
                     f"{report['searchable']}'i aranabilir.")
    return "\n".join(lines)


def to_json(report: dict) -> str:
    data = {key: value for key, value in report.items() if key != "findings"}
    data["findings"] = [vars(finding) for finding in report["findings"]]
    data["has_errors"] = has_errors(report)
    return json.dumps(data, ensure_ascii=False, indent=2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mssql", action="store_true",
                        help="MSSQL sohbet atıflarını da denetle (MSSQL_CONNECTION_STRING gerekir).")
    parser.add_argument("--json", action="store_true", help="Sonucu JSON olarak yaz.")
    args = parser.parse_args(argv)
    try:
        with connect() as connection:
            connection.read_only = True
            report = run_checks(connection)
            if args.mssql:
                from contextlib import closing
                from mssql.connection import connect as mssql_connect
                with closing(mssql_connect()) as mssql_connection:
                    cited = cited_source_ids(mssql_connection)
                report["cited_sources"] = len(cited)
                report["findings"].append(check_citations(connection, cited))
    except DatabaseError as error:
        print(f"KONTROL YAPILAMADI: {error}", file=sys.stderr)
        return 2
    except Exception as error:  # MSSQL bağlantı hataları dahil; bağlantı dizesini yazdırmayız.
        print(f"KONTROL YAPILAMADI: {type(error).__name__}", file=sys.stderr)
        return 2
    print(to_json(report) if args.json else format_report(report))
    return 1 if has_errors(report) else 0


if __name__ == "__main__":
    raise SystemExit(main())
