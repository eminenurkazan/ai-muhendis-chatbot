"""Uygulama günlüğü: maskeleme, bloklamama, olay noktaları, yönetici görüntüleme ve geri alınan gerçek SQL."""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

import api
import app_log
import log_service
import request_context
from mssql.repository import MSSQLRepository, RepositoryError

ROOT = Path(__file__).resolve().parents[1]


class SanitizeTests(unittest.TestCase):
    def test_secret_keys_are_masked_at_any_depth_and_values_truncated(self):
        clean = app_log.sanitize({"password": "p", "Authorization": "Bearer abc", "nested": {"api_key": "k", "ok": "v"},
                                  "access_token": "t", "long": "x" * 1000, "n": 5})
        self.assertEqual((clean["password"], clean["Authorization"], clean["access_token"]), ("[gizli]",) * 3)
        self.assertEqual(clean["nested"], {"api_key": "[gizli]", "ok": "v"})
        self.assertEqual(len(clean["long"]), app_log.MAX_STRING)
        self.assertEqual(clean["n"], 5)

    def test_unserializable_and_oversized_details_are_safe(self):
        self.assertEqual(json.loads(app_log._details_json({"obj": object()}))["obj"][:8], "<object ")
        self.assertEqual(json.loads(app_log._details_json({"a": ["x" * 290] * 20, "b": ["y" * 290] * 20})), {"truncated": True})
        self.assertIsNone(app_log._details_json(None))
        self.assertIsNone(app_log._details_json({"x": float("nan")}) and None)

    def test_depth_and_list_limits(self):
        deep = {"a": {"b": {"c": {"d": {"e": 1}}}}}
        self.assertEqual(app_log.sanitize(deep)["a"]["b"]["c"]["d"], "[derin]")
        self.assertEqual(len(app_log.sanitize(list(range(100)))), 20)


class LogEventTests(unittest.TestCase):
    def test_writes_are_disabled_under_unit_test_runner(self):
        self.assertTrue(app_log._disabled())
        with patch.object(app_log, "_queue") as queue:
            app_log.log_event("info", "x.y")
        queue.put_nowait.assert_not_called()

    def test_queued_record_has_correlation_user_and_sanitized_details(self):
        request_context.new_correlation()
        with patch.object(app_log, "_disabled", return_value=False), patch.object(app_log, "_ensure_worker"), \
             patch.object(app_log, "_queue") as queue:
            app_log.log_event("warning", "auth.login_failed", user_id="u-1", details={"password": "p", "ip": "1.2.3.4"})
        record = queue.put_nowait.call_args.args[0]
        self.assertEqual((record["level"], record["event_type"], record["user_id"]), ("warning", "auth.login_failed", "u-1"))
        self.assertEqual(record["correlation_id"], request_context.correlation_id())
        self.assertEqual(json.loads(record["details_json"]), {"password": "[gizli]", "ip": "1.2.3.4"})

    def test_invalid_level_event_name_and_full_queue_never_raise(self):
        with patch.object(app_log, "_disabled", return_value=False), patch.object(app_log, "_ensure_worker"):
            app_log.log_event("fatal", "x")
            app_log.log_event("info", "")
            app_log.log_event("info", "x" * 101)
            with patch.object(app_log, "_queue") as queue:
                queue.put_nowait.side_effect = Exception("full")
                app_log.log_event("info", "x.y")  # hata yutulur

    def test_write_event_uses_parameters_only(self):
        cursor = MagicMock()
        connection = MagicMock()
        connection.cursor.return_value = cursor
        record = {"user_id": None, "correlation_id": str(uuid4()), "level": "info", "event_type": "a'; DROP TABLE x;--",
                  "details_json": None}
        app_log.write_event(connection, record)
        sql, *params = cursor.execute.call_args.args
        self.assertNotIn("DROP", sql)
        self.assertIn(record["event_type"], params)
        cursor.close.assert_called_once()


class StageTests(unittest.TestCase):
    def test_stage_durations_accumulate_and_isolated_snapshot(self):
        request_context.begin_stages()
        with request_context.stage("embed"):
            pass
        with request_context.stage("llm"):
            pass
        snapshot = request_context.stages_snapshot()
        self.assertEqual(set(snapshot), {"embed", "llm"})
        snapshot["embed"] = 99999
        self.assertNotEqual(request_context.stages_snapshot()["embed"], 99999)

    def test_stage_outside_capture_is_harmless(self):
        request_context._stages.set(None)
        with request_context.stage("embed"):
            pass
        self.assertEqual(request_context.stages_snapshot(), {})


class EventPointTests(unittest.TestCase):
    def setUp(self):
        self.previous = api.app.dependency_overrides.copy()
        self.addCleanup(self.restore)
        self.owner = str(uuid4())
        api.app.dependency_overrides[api.require_user] = lambda: {"id": self.owner, "role": "user"}
        self.client = TestClient(api.app)
        self.chat, self.request = str(uuid4()), str(uuid4())

    def restore(self):
        api.app.dependency_overrides.clear()
        api.app.dependency_overrides.update(self.previous)

    def test_completed_ask_logs_measurements_but_never_question_or_answer(self):
        result = {"answer": "SECRET-ANSWER", "used_ticket_ids": ["1"], "insufficient_context": False,
                  "retrieved_ticket_ids": ["1"], "elapsed_ms": 1234, "expertise_mode": "oracle_db",
                  "prompt_version": "v", "used_source_ids": ["1"], "retrieved_source_ids": ["1"], "sources": [],
                  "stage_ms": {"embed": 200, "retrieve": 30, "llm": 1000}}
        with patch("rag_service.ask_question", return_value=result), patch("app_log.log_event") as log, \
             patch("chat_service.answer_chat", side_effect=lambda u, c, q, r, generate: generate(q)):
            response = self.client.post(f"/chats/{self.chat}/ask", json={"question": "SECRET-QUESTION", "request_id": self.request})
        self.assertEqual(response.status_code, 200)
        self.assertIn("X-Request-ID", response.headers)
        level, event = log.call_args.args[:2]
        self.assertEqual((level, event), ("info", "chat.ask_completed"))
        details = log.call_args.kwargs["details"]
        self.assertEqual((details["stage_ms"], details["elapsed_ms"], details["mode"]), (result["stage_ms"], 1234, "oracle_db"))
        self.assertNotIn("SECRET", json.dumps(log.call_args.kwargs, default=str))

    def test_failures_are_logged_with_status_and_error_type_only(self):
        import chat_service
        for error, status, level in ((chat_service.ChatNotFound("Sohbet bulunamadı."), 404, "warning"),
                                     (chat_service.ChatUnavailable("x"), 503, "error"),
                                     (RuntimeError("sk-secret-token"), 502, "error")):
            with self.subTest(status=status), patch("app_log.log_event") as log, \
                 patch("chat_service.answer_chat", side_effect=error):
                response = self.client.post(f"/chats/{self.chat}/ask", json={"question": "q", "request_id": str(uuid4())})
            self.assertEqual(response.status_code, status)
            failed = [call for call in log.call_args_list if call.args[1] == "chat.ask_failed"]
            self.assertEqual(len(failed), 1)
            self.assertEqual(failed[0].args[:2], (level, "chat.ask_failed"))
            self.assertEqual(failed[0].kwargs["details"]["status"], status)
            self.assertNotIn("secret", json.dumps([c.kwargs for c in log.call_args_list], default=str))

    def test_feedback_logs_rating_but_not_comment(self):
        with patch("app_log.log_event") as log, patch("chat_service.save_feedback", return_value={"rating": 4, "comment": "GİZLİ YORUM"}):
            response = self.client.put(f"/chats/{self.chat}/requests/{self.request}/feedback",
                                       json={"rating": 4, "comment": "GİZLİ YORUM"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(log.call_args.kwargs["details"], {"chat_id": self.chat, "rating": 4, "has_comment": True})

    def test_login_failure_logs_ip_not_email_or_password(self):
        import auth_service
        api.app.dependency_overrides.clear()
        with patch("app_log.log_event") as log, patch("auth_service.login", side_effect=auth_service.AuthenticationError("hatalı")):
            response = TestClient(api.app).post("/auth/login", json={"email": "kisi@example.com", "password": "Sifre123!"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(log.call_args.args[:2], ("warning", "auth.login_failed"))
        text = json.dumps(log.call_args.kwargs, default=str)
        self.assertNotIn("kisi@example.com", text)
        self.assertNotIn("Sifre123", text)

    def test_unhandled_exception_is_logged_by_middleware(self):
        @api.app.get("/_boom")
        def boom():
            raise RuntimeError("secret-detail")
        self.addCleanup(lambda: api.app.router.routes.__setitem__(slice(None), [r for r in api.app.router.routes if getattr(r, "path", None) != "/_boom"]))
        with patch("app_log.log_event") as log:
            with self.assertRaises(RuntimeError):
                self.client.get("/_boom")
        self.assertEqual(log.call_args.args[:2], ("error", "http.unhandled_exception"))
        self.assertNotIn("secret-detail", json.dumps(log.call_args.kwargs, default=str))


class AdminLogApiTests(unittest.TestCase):
    def setUp(self):
        self.previous = api.app.dependency_overrides.copy()
        self.addCleanup(self.restore)
        self.client = TestClient(api.app)

    def restore(self):
        api.app.dependency_overrides.clear()
        api.app.dependency_overrides.update(self.previous)

    def as_role(self, role):
        api.app.dependency_overrides[api.require_user] = lambda: {"id": str(uuid4()), "role": role}

    def test_requires_login_and_admin(self):
        with patch("log_service.list_logs") as listing, patch("log_service.summary") as summary:
            self.assertEqual(self.client.get("/admin/logs").status_code, 401)
            self.assertEqual(self.client.get("/admin/logs/summary").status_code, 401)
            self.as_role("user")
            self.assertEqual(self.client.get("/admin/logs").status_code, 403)
            self.assertEqual(self.client.get("/admin/logs/summary").status_code, 403)
        listing.assert_not_called()
        summary.assert_not_called()

    def test_admin_lists_with_validated_filters(self):
        self.as_role("admin")
        page = {"items": [{"id": str(uuid4()), "created_at": "2026-11-12T10:00:00Z", "level": "info",
                           "event_type": "chat.ask_completed", "correlation_id": str(uuid4()),
                           "user_email": "a@example.com", "details": {"elapsed_ms": 5}}], "next_offset": None}
        with patch("log_service.list_logs", return_value=page) as listing:
            response = self.client.get("/admin/logs?days=30&level=error&event_type=chat.ask_failed&q=abc&offset=50&limit=20")
        self.assertEqual(response.status_code, 200)
        listing.assert_called_once_with(days=30, level="error", event_type="chat.ask_failed", query="abc", offset=50, limit=20)
        for query in ("days=0", "days=366", "level=fatal", "limit=101", "offset=-1", "event_type=" + "x" * 101):
            self.assertEqual(self.client.get("/admin/logs?" + query).status_code, 422)

    def test_database_failure_is_safe_503(self):
        self.as_role("admin")
        with patch("log_service.list_logs", side_effect=log_service.LogsUnavailable("Günlüklere şu anda ulaşılamıyor.")):
            response = self.client.get("/admin/logs")
        self.assertEqual((response.status_code, response.json()["detail"]), (503, "Günlüklere şu anda ulaşılamıyor."))

    def test_service_parses_details_and_handles_corrupt_json(self):
        from datetime import datetime
        rows = [{"id": uuid4(), "created_at": datetime(2026, 11, 12, 10), "level": "info", "event_type": "a",
                 "correlation_id": uuid4(), "user_email": None, "details_json": '{"x": 1}'},
                {"id": uuid4(), "created_at": datetime(2026, 11, 12, 11), "level": "error", "event_type": "b",
                 "correlation_id": uuid4(), "user_email": None, "details_json": "{bozuk"}]
        repository = MagicMock()
        repository.admin_logs.return_value = {"items": rows, "next_offset": None}
        with patch.object(log_service.database, "connect", return_value=MagicMock()), \
             patch.object(log_service, "MSSQLRepository", return_value=repository):
            page = log_service.list_logs(days=7)
        self.assertEqual((page["items"][0]["details"], page["items"][1]["details"]), ({"x": 1}, None))
        self.assertIsNotNone(page["items"][0]["created_at"].tzinfo)

    def test_repository_builds_parameterized_sql_and_validates(self):
        repository = object.__new__(MSSQLRepository)
        captured = []
        repository._query = lambda sql, *params: captured.append((sql, params)) or []
        repository.admin_logs(days=7, level="error", event_type="x", query="a_b%", offset=0, limit=10)
        sql, params = captured[0]
        self.assertEqual(sql.count("?"), len(params))
        self.assertNotIn("a_b", sql)
        self.assertIn("a\\_b\\%", "".join(str(p) for p in params))
        corr = str(uuid4())
        repository.admin_logs(days=1, query=corr)
        self.assertIn("correlation_id = ?", captured[1][0])
        for bad in ({"days": 0}, {"limit": 0}, {"level": "fatal"}, {"offset": -1}, {"days": True}):
            with self.assertRaises(ValueError):
                repository.admin_logs(**bad)


class LogUiTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch("ui_client.current_user", side_effect=lambda *a: {"email": "a@example.com", "role": self.role}))
        self.stack.enter_context(patch("ui_client.list_chats", return_value={"items": [], "next_offset": None}))
        self.summary = self.stack.enter_context(patch("ui_client.log_summary", return_value={
            "levels": {"error": 2, "warning": 3, "info": 40}, "events": [{"event_type": "chat.ask_completed", "count": 40}]}))
        entry = {"id": str(uuid4()), "created_at": "2026-11-12T10:00:00Z", "level": "info", "event_type": "chat.ask_completed",
                 "correlation_id": str(uuid4()), "user_email": "a@example.com", "details": {"elapsed_ms": 1200, "stage_ms": {"llm": 1000}}}
        self.logs = self.stack.enter_context(patch("ui_client.logs", return_value={"items": [entry], "next_offset": None}))

    def app(self, role):
        self.role = role
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"))
        app.session_state.token = "test-only"
        app.session_state.user = {"email": "a@example.com", "role": role}
        app.session_state.messages = []
        app.session_state.expertise = "service_desk"
        app.session_state.view = "admin"
        app.session_state.admin_section = "Günlükler"
        return app

    def test_admin_sees_counts_table_and_details(self):
        app = self.app("admin").run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual([m.label for m in app.metric], ["Hata", "Uyarı", "Bilgi"])
        self.assertEqual([m.value for m in app.metric], ["2", "3", "40"])
        self.assertTrue(app.dataframe)
        self.assertTrue(app.json)

    def test_filter_values_reach_the_api(self):
        app = self.app("admin").run(timeout=20)
        app.selectbox(key="log_level").set_value("Hata").run(timeout=20)
        self.assertEqual(self.logs.call_args.kwargs["level"], "error")

    def test_non_admin_never_reaches_logs(self):
        app = self.app("user").run(timeout=20)
        self.assertFalse(app.exception)
        self.summary.assert_not_called()
        self.logs.assert_not_called()


@unittest.skipUnless(os.environ.get("APP_LOG_SQL_TEST"), "Explicit rollback-only SQL test not enabled")
class LogSqlTests(unittest.TestCase):
    def test_write_read_filter_and_roll_back(self):
        from mssql import connection as database
        connection = database.connect()
        try:
            repository = MSSQLRepository(connection)
            user = repository.create_user(f"log-test-{uuid4()}@example.com", "test-only-not-a-login-hash")
            marker, other = str(uuid4()), str(uuid4())
            for level, event, corr, who in (("error", "test.marker_a", marker, str(user["id"])),
                                            ("info", "test.marker_b", other, None)):
                app_log.write_event(connection, {"user_id": who, "correlation_id": corr, "level": level,
                                                 "event_type": event, "details_json": app_log._details_json({"password": "p", "n": 1})})
            by_corr = repository.admin_logs(days=1, query=marker)["items"]
            self.assertEqual([r["event_type"] for r in by_corr], ["test.marker_a"])
            self.assertEqual(by_corr[0]["user_email"], user["email"])
            self.assertEqual(json.loads(by_corr[0]["details_json"]), {"password": "[gizli]", "n": 1})
            self.assertEqual([r["event_type"] for r in repository.admin_logs(days=1, level="info", event_type="test.marker_b")["items"]],
                             ["test.marker_b"])
            self.assertEqual(len(repository.admin_logs(days=1, query=user["email"])["items"]), 1)
            summary = repository.log_summary(days=1)
            self.assertGreaterEqual(summary["levels"].get("error", 0), 1)
            self.assertIn("test.marker_a", [e["event_type"] for e in summary["events"]])
        finally:
            connection.rollback()
            connection.close()


if __name__ == "__main__":
    unittest.main()
