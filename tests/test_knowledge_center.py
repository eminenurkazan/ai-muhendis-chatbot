"""Bilgi Merkezi: doğrulama, yönetici yetkisi ve (isteğe bağlı) geri alınan gerçek PostgreSQL testi."""
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

import api
import kb_service as service
import rag_provider

ROOT = Path(__file__).resolve().parents[1]
HEADER = "issueid,problem,solution\n"


class CsvTests(unittest.TestCase):
    def test_valid_rows_and_optional_columns(self):
        records, errors = service.parse_tickets_csv(
            "issueid,problem,solution,category,solution_scope,resolution_confirmed\n"
            "T1,Yazıcı çalışmıyor,Sürücüyü yeniden kur,Donanım,procedure,true\n", "general_it")
        self.assertEqual((len(records), errors), (1, []))

    def test_bom_is_accepted(self):
        records, errors = service.parse_tickets_csv("﻿" + HEADER + "A,p,s\n", "general_it")
        self.assertEqual((len(records), errors), (1, []))

    def test_missing_unknown_columns_and_domain_are_rejected(self):
        for content, domain in (("issueid,problem\nA,p\n", "general_it"),
                                (HEADER.strip() + ",extra\nA,p,s,x\n", "general_it"),
                                (HEADER + "A,p,s\n", "baska_alan"), ("", "general_it")):
            with self.subTest(content=content[:30]), self.assertRaises(service.KnowledgeError):
                service.parse_tickets_csv(content, domain)

    def test_row_errors_are_listed_with_line_numbers_and_never_include_values(self):
        long_text = "x" * (service.MAX_FIELD + 1)
        records, errors = service.parse_tickets_csv(
            HEADER + f"A,p,s\nA,p2,s2\nB,,s\nC,{long_text},s\nD,p,s,extra\n"
            "E,p,s\n".replace("E", "F"), "general_it")
        self.assertEqual([r["issueid"] for r in records], ["A", "F"])
        joined = "\n".join(errors)
        for expected in ("Satır 3", "yinelenen", "Satır 4", "Satır 5", "Satır 6"):
            self.assertIn(expected, joined)
        self.assertNotIn(long_text, joined)

    def test_row_limit(self):
        rows = "".join(f"I{n},p,s\n" for n in range(service.MAX_ROWS + 1))
        with self.assertRaises(service.KnowledgeError):
            service.parse_tickets_csv(HEADER + rows, "general_it")


class LimitTests(unittest.TestCase):
    def test_environment_overrides_are_clamped_and_invalid_values_fall_back(self):
        import importlib
        import kb_limits
        original = {k: os.environ.get(k) for k in ("KB_MAX_UPLOAD_CHARS", "KB_MAX_ROWS")}
        self.addCleanup(lambda: [os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
                                 for k, v in original.items()] and importlib.reload(kb_limits))
        for rows, chars, expected in (("2000", "5000000", (2000, 5_000_000)), ("abc", "-3", (500, 1)),
                                      ("99999999", "99999999999", (20_000, 20_000_000)), ("", "", (500, 1_000_000))):
            os.environ["KB_MAX_ROWS"], os.environ["KB_MAX_UPLOAD_CHARS"] = rows, chars
            importlib.reload(kb_limits)
            self.assertEqual((kb_limits.MAX_ROWS, kb_limits.MAX_UPLOAD_CHARS), expected)


class GuideTests(unittest.TestCase):
    def guide(self):
        return json.loads((ROOT / "data_sources/official_guides/microsoft_ad_replication.json").read_text(encoding="utf-8"))

    def test_valid_guide_and_list(self):
        for payload in (self.guide(), [self.guide()]):
            records, errors = service.parse_guides_json(json.dumps(payload))
            self.assertEqual((len(records), errors), (1, []))

    def test_duplicate_wrong_host_and_bad_json_are_rejected(self):
        records, errors = service.parse_guides_json(json.dumps([self.guide(), self.guide()]))
        self.assertEqual((len(records), len(errors)), (1, 1))
        bad = self.guide()
        bad["source_url"] = "https://example.com/rehber"
        records, errors = service.parse_guides_json(json.dumps(bad))
        self.assertEqual((records, len(errors)), ([], 1))
        for content in ("not json", "[]"):
            with self.assertRaises(service.KnowledgeError):
                service.parse_guides_json(content)


class KnowledgeApiTests(unittest.TestCase):
    def setUp(self):
        self.previous = api.app.dependency_overrides.copy()
        self.addCleanup(self.restore)
        self.client = TestClient(api.app)
        self.body = {"kind": "tickets_csv", "filename": "x.csv", "content": HEADER + "A,p,s\n",
                     "license_note": "Dahili kayıt", "dry_run": True}

    def restore(self):
        api.app.dependency_overrides.clear()
        api.app.dependency_overrides.update(self.previous)

    def as_role(self, role):
        api.app.dependency_overrides[api.require_user] = lambda: {"id": str(uuid4()), "role": role}

    def test_every_endpoint_requires_login_then_admin(self):
        record = str(uuid4())
        calls = [("get", "/admin/kb/summary", None), ("get", "/admin/kb/records", None),
                 ("post", "/admin/kb/upload", self.body), ("post", "/admin/kb/approve", {"ids": [record]}),
                 ("post", f"/admin/kb/records/{record}/status", {"excluded": True})]
        with patch("kb_service.summary") as summary, patch("kb_service.list_records") as listing, \
             patch("kb_service.stage_tickets") as stage, patch("kb_service.approve_record") as approve, \
             patch("kb_service.exclude_record") as exclude:
            for role in (None, "user"):
                if role:
                    self.as_role(role)
                for method, path, body in calls:
                    with self.subTest(role=role, path=path):
                        response = getattr(self.client, method)(path, **({"json": body} if body else {}))
                        self.assertEqual(response.status_code, 403 if role else 401)
            for mocked in (summary, listing, stage, approve, exclude):
                mocked.assert_not_called()

    def test_dry_run_validates_without_database(self):
        self.as_role("admin")
        with patch("kb_api.connect") as connect:
            response = self.client.post("/admin/kb/upload", json=self.body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.json()["valid"], response.json()["added"]), (1, 0))
        connect.assert_not_called()

    def test_upload_requires_license_note_and_valid_file(self):
        self.as_role("admin")
        self.assertEqual(self.client.post("/admin/kb/upload", json={**self.body, "license_note": " "}).status_code, 422)
        bad = {**self.body, "content": HEADER + ",p,s\n", "dry_run": False}
        with patch("kb_api.connect") as connect:
            response = self.client.post("/admin/kb/upload", json=bad)
        self.assertEqual(response.status_code, 422)
        connect.assert_not_called()  # hatalı dosyada hiçbir şey yazılmaz
        for extra in ({"kind": "exe"}, {"unknown": 1}, {"content": ""}, {"domain": "x"}):
            self.assertEqual(self.client.post("/admin/kb/upload", json={**self.body, **extra}).status_code, 422)

    def test_approve_limits_and_partial_failure_hide_details(self):
        self.as_role("admin")
        ids = [str(uuid4()) for _ in range(2)]
        self.assertEqual(self.client.post("/admin/kb/approve", json={"ids": [str(uuid4()) for _ in range(11)]}).status_code, 422)
        self.assertEqual(self.client.post("/admin/kb/approve", json={"ids": []}).status_code, 422)

        def fake(connection, record_id, embed):
            if record_id == ids[1]:
                raise rag_provider.ServiceUnavailable("Cloudflare bilgileri hazır değil.")
            return {"status": "indexed"}
        with patch("kb_api.connect"), patch("kb_service.approve_record", side_effect=fake):
            response = self.client.post("/admin/kb/approve", json={"ids": ids})
        self.assertEqual([item["status"] for item in response.json()["items"]], ["indexed", "failed"])
        with patch("kb_api.connect"), patch("kb_service.approve_record", side_effect=RuntimeError("sk-secret-token")):
            response = self.client.post("/admin/kb/approve", json={"ids": ids[:1]})
        self.assertNotIn("secret", response.text)

    def test_database_failure_is_safe_503(self):
        self.as_role("admin")
        from database.connection import DatabaseError
        with patch("kb_api.connect", side_effect=DatabaseError("postgresql://user:pass@host/db")):
            response = self.client.get("/admin/kb/summary")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("pass", response.text)


class KnowledgeUiTests(unittest.TestCase):
    PENDING, ACTIVE = str(uuid4()), str(uuid4())

    def setUp(self):
        from contextlib import ExitStack
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.role = "admin"
        self.stack.enter_context(patch("ui_client.current_user", side_effect=lambda *a: {"email": "a@example.com", "role": self.role}))
        self.stack.enter_context(patch("ui_client.list_chats", return_value={"items": [], "next_offset": None}))
        self.summary = self.stack.enter_context(patch("ui_client.kb_summary", return_value={
            "groups": [{"record_type": "ticket", "domain": "general_it", "review_status": "pending", "count": 1},
                       {"record_type": "documentation", "domain": "oracle_db", "review_status": "approved", "count": 1}],
            "total": 2, "searchable": 1, "chunks": 1}))
        item = lambda rid, status: {"id": rid, "source_record_id": f"K-{status}", "record_type": "ticket",
                                    "domain": "general_it", "title": "t", "review_status": status,
                                    "index_status": "pending", "source_name": "Admin yüklemesi: x.csv",
                                    "license": "test", "problem": "Örnek problem metni"}
        self.records = self.stack.enter_context(patch("ui_client.kb_records", return_value={
            "items": [item(self.PENDING, "pending"), item(self.ACTIVE, "approved")], "total": 2, "next_offset": None}))
        self.approve = self.stack.enter_context(patch("ui_client.kb_approve", return_value={
            "items": [{"id": self.PENDING, "status": "indexed", "message": ""}]}))
        self.toggle = self.stack.enter_context(patch("ui_client.kb_set_status", return_value={"status": "excluded"}))

    def app(self, role="admin"):
        from streamlit.testing.v1 import AppTest
        self.role = role
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"))
        app.session_state.token = "test-only"
        app.session_state.user = {"email": "a@example.com", "role": role}
        app.session_state.messages = []
        app.session_state.expertise = "service_desk"
        app.session_state.view = "admin"
        app.session_state.admin_section = "Bilgi Merkezi"
        return app

    def test_section_shows_counts_and_records(self):
        app = self.app().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual([m.label for m in app.metric][:4], ["Toplam kayıt", "Aranabilir", "Onay bekleyen", "Devre dışı"])
        self.assertTrue(app.dataframe)
        self.records.assert_called()

    def test_page_bulk_approve_sends_groups_of_at_most_ten(self):
        ids = [str(uuid4()) for _ in range(12)]
        self.records.return_value = {"items": [
            {"id": rid, "source_record_id": f"K{n}", "record_type": "ticket", "domain": "general_it", "title": "t",
             "review_status": "pending", "index_status": "pending", "source_name": "s", "license": "l",
             "problem": "p"} for n, rid in enumerate(ids)], "total": 12, "next_offset": None}
        self.approve.side_effect = lambda base, token, group: {"items": [
            {"id": g, "status": "indexed", "message": ""} for g in group]}
        app = self.app().run(timeout=20)
        next(b for b in app.button if b.label.startswith("Sayfadaki 12")).click().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual([len(call.args[2]) for call in self.approve.call_args_list], [10, 2])

    def test_non_admin_never_reaches_knowledge_center(self):
        app = self.app("user").run(timeout=20)
        self.assertFalse(app.exception)
        self.summary.assert_not_called()
        self.records.assert_not_called()

    def test_pending_record_can_be_approved_and_active_one_excluded(self):
        app = self.app().run(timeout=20)
        app.multiselect(key="kb_approve_ids").set_value([self.PENDING]).run(timeout=20)
        next(b for b in app.button if b.label == "Seçilenleri indeksle ve onayla").click().run(timeout=20)
        self.assertFalse(app.exception)
        self.approve.assert_called_once()
        self.assertEqual([str(i) for i in self.approve.call_args.args[2]], [self.PENDING])
        app = self.app().run(timeout=20)
        app.selectbox(key="kb_status_id").set_value(self.ACTIVE).run(timeout=20)
        next(b for b in app.button if b.label == "Devre dışı bırak").click().run(timeout=20)
        self.toggle.assert_called_once()
        self.assertEqual(self.toggle.call_args.args[2:], (self.ACTIVE, True))


@unittest.skipUnless(os.environ.get("KB_SQL_TEST") and os.environ.get("DATABASE_URL"),
                     "Explicit rollback-only PostgreSQL test not enabled")
class KnowledgeSqlTests(unittest.TestCase):
    def test_stage_approve_exclude_restore_with_rollback(self):
        from database.connection import connect
        vector = [1.0] + [0.0] * 1023
        connection = connect()
        try:
            before = service.summary(connection)
            marker = f"kb-test-{uuid4()}"
            csv_text = HEADER + f"{marker},Test problemi,Test çözümü\n"
            records, errors = service.parse_tickets_csv(csv_text, "windows_server")
            self.assertEqual(errors, [])
            staged = service.stage_tickets(connection, records, domain="windows_server", filename="t.csv",
                                           license_note="test", file_digest=marker.ljust(32, "0"))
            self.assertEqual(staged, {"added": 1, "already_present": 0})
            again = service.stage_tickets(connection, records, domain="windows_server", filename="t.csv",
                                          license_note="test", file_digest=marker.ljust(32, "0"))
            self.assertEqual(again, {"added": 0, "already_present": 1})
            after = service.summary(connection)
            self.assertEqual(after["total"] - before["total"], 1)
            self.assertEqual(after["searchable"], before["searchable"])  # pending: aranamaz
            record = service.list_records(connection, query=marker)["items"][0]
            self.assertEqual((record["review_status"], record["domain"]), ("pending", "windows_server"))
            self.assertEqual(service.approve_record(connection, record["id"], lambda text: vector)["status"], "indexed")
            self.assertEqual(service.summary(connection)["searchable"], before["searchable"] + 1)
            self.assertEqual(service.approve_record(connection, record["id"], lambda text: 1 / 0)["status"], "already")
            self.assertEqual(service.exclude_record(connection, record["id"], True)["status"], "excluded")
            self.assertEqual(service.summary(connection)["searchable"], before["searchable"])
            self.assertEqual(service.exclude_record(connection, record["id"], False)["status"], "approved")
            self.assertEqual(service.summary(connection)["searchable"], before["searchable"] + 1)
            self.assertEqual(service.list_records(connection, review_status="pending", query=marker)["total"], 0)
        finally:
            connection.rollback()
            connection.close()


if __name__ == "__main__":
    unittest.main()
