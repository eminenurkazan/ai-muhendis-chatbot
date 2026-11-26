"""database.check_sync: rapor, çıkış kodu, MSSQL atıf kontrolü ve gerçek PostgreSQL'de bozuk veri tespiti."""
import io
import json
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from database import check_sync as sync


def finding(key, level, count, sample=()):
    return sync.Finding(key, level, f"{key} başlığı", "açıklama", count, list(sample))


def report(*findings):
    return {"records": 3, "chunks": 3, "approved_ready": 3, "searchable": 3, "findings": list(findings)}


class ReportTests(unittest.TestCase):
    def test_only_error_level_findings_fail(self):
        self.assertFalse(sync.has_errors(report(finding("a", "hata", 0), finding("b", "bilgi", 5))))
        self.assertTrue(sync.has_errors(report(finding("a", "hata", 1, ["x"]))))

    def test_text_report_marks_levels_and_truncates_sample(self):
        text = sync.format_report(report(finding("a", "hata", 25, [str(n) for n in range(20)]),
                                         finding("b", "bilgi", 1, ["y"]), finding("c", "hata", 0)))
        self.assertIn("[HATA ] a başlığı: 25", text)
        self.assertIn("(+5 daha)", text)
        self.assertIn("[BİLGİ] b başlığı: 1", text)
        self.assertIn("[TAMAM] c başlığı: 0", text)
        self.assertIn("SONUÇ: Tutarsızlık var", text)

    def test_json_report(self):
        data = json.loads(sync.to_json(report(finding("a", "bilgi", 1, ["x"]))))
        self.assertFalse(data["has_errors"])
        self.assertEqual(data["findings"][0]["sample"], ["x"])

    def test_every_check_selects_identifier_first(self):
        for check in sync.CHECKS:
            with self.subTest(check=check.key):
                self.assertIn(check.level, {"hata", "bilgi"})
                self.assertRegex(check.sql.split("FROM")[0], r"source_record_id")


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


class CitationTests(unittest.TestCase):
    def test_missing_citations_are_reported_as_info(self):
        class Connection:
            def execute(self, sql, params):
                self.params = params
                return FakeResult([("a",)])
        connection = Connection()
        result = sync.check_citations(connection, ["a", "b"])
        self.assertEqual((result.level, result.count, result.sample), ("bilgi", 1, ["b"]))
        self.assertEqual(connection.params["ids"], ["a", "b"])

    def test_no_citations_needs_no_query(self):
        self.assertEqual(sync.check_citations(object(), []).count, 0)


class MainTests(unittest.TestCase):
    def run_main(self, fake_report, *args):
        class Connection:
            read_only = False
            def __enter__(self):
                return self
            def __exit__(self, *exc):
                return False
        out = io.StringIO()
        with patch.object(sync, "connect", return_value=Connection()), \
                patch.object(sync, "run_checks", return_value=fake_report), patch("sys.stdout", out):
            code = sync.main(list(args))
        return code, out.getvalue()

    def test_exit_codes(self):
        self.assertEqual(self.run_main(report(finding("a", "bilgi", 2, ["x", "y"])))[0], 0)
        self.assertEqual(self.run_main(report(finding("a", "hata", 1, ["x"])))[0], 1)

    def test_database_error_is_safe(self):
        err = io.StringIO()
        with patch.object(sync, "connect", side_effect=sync.DatabaseError("DATABASE_URL tanımlı değil.")), \
                patch("sys.stderr", err):
            self.assertEqual(sync.main([]), 2)
        self.assertIn("KONTROL YAPILAMADI", err.getvalue())


@unittest.skipUnless(os.environ.get("SYNC_SQL_TEST") and os.environ.get("DATABASE_URL"),
                     "Rollback-only PostgreSQL test not enabled (SYNC_SQL_TEST=1)")
class SyncSqlTests(unittest.TestCase):
    """Her tutarsızlık türü bilerek oluşturulur; kontrolün yakaladığı doğrulanır; işlem geri alınır."""

    def test_detects_each_inconsistency(self):
        from database.connection import connect
        vector = [1.0] + [0.0] * 1023
        marker = f"sync-test-{uuid4()}"
        connection = connect()
        try:
            baseline = sync.run_checks(connection)
            source = connection.execute(
                "INSERT INTO knowledge_sources (name, source_type, source_version) VALUES (%s, 'test', 'v1') "
                "RETURNING id", (marker,)).fetchone()[0]

            def record(suffix, review, index, content_hash="h1"):
                return connection.execute(
                    "INSERT INTO knowledge_records (source_id, source_record_id, problem, solution, review_status, "
                    "index_status, content_hash) VALUES (%s, %s, 'p', 's', %s, %s, %s) RETURNING id",
                    (source, f"{marker}-{suffix}", review, index, content_hash)).fetchone()[0]

            def chunk(record_id, index=0, content_hash="h1", model=sync.EMBEDDING_MODEL):
                connection.execute(
                    "INSERT INTO knowledge_chunks (record_id, chunk_index, chunk_text, embedding, embedding_model, "
                    "record_content_hash) VALUES (%s, %s, 't', %s, %s, %s)",
                    (record_id, index, vector, model, content_hash))

            chunk(record("ok", "approved", "ready"))
            record("nochunk", "approved", "ready")
            chunk(record("stale", "approved", "ready", content_hash="h2"), content_hash="h1")
            chunk(record("model", "approved", "ready"), model="baska-model")
            chunk(record("gap", "approved", "ready"), index=1)
            chunk(record("pendready", "pending", "ready"))
            record("waiting", "approved", "pending")
            chunk(record("excluded", "excluded", "ready"))

            result = sync.run_checks(connection)
            found = {f.key: set(f.sample) for f in result["findings"]}
            expect = {
                "ready_without_chunk": "nochunk", "stale_vector": "stale", "foreign_model": "model",
                "chunk_index_gap": "gap", "ready_not_approved": "pendready",
                "approved_not_ready": "waiting", "excluded_with_chunk": "excluded",
            }
            for key, suffix in expect.items():
                with self.subTest(check=key):
                    self.assertIn(f"{marker}-{suffix}", found[key])
            flagged = set().union(*found.values())
            self.assertNotIn(f"{marker}-ok", flagged)
            self.assertTrue(sync.has_errors(result))
            # Aranabilir sayısına yalnız "ok" ve "gap" (hash ve model doğru) eklenir.
            self.assertEqual(result["searchable"] - baseline["searchable"], 2)

            citation = sync.check_citations(connection, [f"{marker}-ok", f"{marker}-stale", f"{marker}-yok"])
            self.assertEqual(set(citation.sample), {f"{marker}-stale", f"{marker}-yok"})
        finally:
            connection.rollback()
            connection.close()


if __name__ == "__main__":
    unittest.main()
