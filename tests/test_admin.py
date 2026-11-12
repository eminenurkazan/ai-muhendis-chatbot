"""Admin report: role enforcement, aggregate maths, UI visibility; no cloud calls."""
from contextlib import ExitStack
import os
from pathlib import Path
import unittest
from unittest.mock import ANY, Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

import admin_service
import api
import ui_client
from mssql.repository import MSSQLRepository, RepositoryError

RAW = {
    "days": 30, "users_total": 3, "users_active": 2, "chats": 4, "questions": 10, "answers": 8,
    "answers_with_sources": 6, "avg_latency_ms": 9300, "rated_total": 4, "satisfied": 3,
    "rating_distribution": {1: 0, 2: 1, 3: 0, 4: 2, 5: 1}, "avg_rating": 4.0,
    "top_questions": [{"question": "chrome açılmıyor", "asked": 3, "rated": 1, "avg_rating": 5.0}],
    "by_mode": [{"expertise_mode": "service_desk", "questions": 7}],
    "daily": [{"day": "2026-11-12", "questions": 10}],
}


class AdminApiTests(unittest.TestCase):
    def setUp(self):
        self.previous = api.app.dependency_overrides.copy()
        self.addCleanup(self.restore)
        self.client = TestClient(api.app)

    def restore(self):
        api.app.dependency_overrides.clear()
        api.app.dependency_overrides.update(self.previous)

    def as_role(self, role):
        api.app.dependency_overrides[api.require_user] = lambda: {"id": str(uuid4()), "role": role}

    def test_requires_login_and_admin_role(self):
        with patch("admin_service.report") as report:
            self.assertEqual(self.client.get("/admin/report").status_code, 401)
            self.as_role("user")
            self.assertEqual(self.client.get("/admin/report").status_code, 403)
            report.assert_not_called()

    def test_admin_gets_report_with_rates_and_validated_params(self):
        self.as_role("admin")
        with patch("admin_service.report", side_effect=lambda d, t:
                   {**RAW, "days": d, "satisfaction_rate": 75.0, "source_answer_rate": 75.0,
                    "rating_coverage": 50.0}) as report:
            result = self.client.get("/admin/report?days=7&top=5")
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()["days"], 7)
            self.assertEqual(result.json()["rating_distribution"]["5"], 1)
            report.assert_called_once_with(7, 5)
            for query in ("days=0", "days=366", "top=0", "top=51", "days=x"):
                self.assertEqual(self.client.get("/admin/report?" + query).status_code, 422)

    def test_unavailable_database_is_safe_503(self):
        self.as_role("admin")
        with patch("admin_service.report", side_effect=admin_service.ReportUnavailable("Rapor yok.")):
            result = self.client.get("/admin/report")
        self.assertEqual((result.status_code, result.json()["detail"]), (503, "Rapor yok."))


class AdminServiceTests(unittest.TestCase):
    def run_report(self, raw):
        connection, repository = Mock(), Mock()
        repository.admin_report.return_value = dict(raw)
        with patch.object(admin_service.database, "connect", return_value=connection), \
             patch.object(admin_service, "MSSQLRepository", return_value=repository):
            result = admin_service.report(30, 10)
        connection.close.assert_called_once()
        return result

    def test_rates(self):
        result = self.run_report(RAW)
        self.assertEqual(result["satisfaction_rate"], 75.0)
        self.assertEqual(result["source_answer_rate"], 75.0)
        self.assertEqual(result["rating_coverage"], 50.0)

    def test_empty_data_has_no_rates_instead_of_zero_division(self):
        result = self.run_report({**RAW, "answers": 0, "answers_with_sources": 0, "rated_total": 0, "satisfied": 0})
        self.assertTrue(all(result[key] is None for key in ("satisfaction_rate", "source_answer_rate", "rating_coverage")))

    def test_database_error_hides_details(self):
        repository = Mock()
        repository.admin_report.side_effect = RepositoryError("private SQL details")
        with patch.object(admin_service.database, "connect", return_value=Mock()), \
             patch.object(admin_service, "MSSQLRepository", return_value=repository):
            with self.assertRaises(admin_service.ReportUnavailable) as error:
                admin_service.report()
        self.assertNotIn("private", str(error.exception))


class AdminRepositoryTests(unittest.TestCase):
    def test_parameters_are_validated_and_queries_are_read_only(self):
        repository = object.__new__(MSSQLRepository)
        repository._query = Mock()
        for days, top in ((0, 10), (366, 10), (30, 0), (30, 51), (True, 10), ("30", 10)):
            with self.subTest(days=days, top=top), self.assertRaises(ValueError):
                repository.admin_report(days, top)
        repository._query.assert_not_called()

    def test_report_shape_and_no_write_statements(self):
        repository = object.__new__(MSSQLRepository)
        totals = {"users_total": 3, "users_active": 2, "chats": 1, "questions": 2, "answers": 2,
                  "no_context_answers": 1, "avg_latency_ms": 1234.6}
        repository._query = Mock(side_effect=[
            [totals], [{"rating": 5, "n": 1}, {"rating": 3, "n": 1}],
            [{"question": "q", "asked": 2, "avg_rating": 4.0, "rated": 2}],
            [{"expertise_mode": "oracle_db", "questions": 2}], [{"day": "2026-11-12", "questions": 2}]])
        report = repository.admin_report(7, 5)
        self.assertEqual((report["answers_with_sources"], report["avg_latency_ms"], report["avg_rating"]), (1, 1235, 4.0))
        self.assertEqual(report["satisfied"], 1)
        for call in repository._query.call_args_list:
            sql = call.args[0].upper()
            self.assertEqual(sql.count("?"), len(call.args) - 1)  # placeholders match parameters
            self.assertTrue(sql.startswith("SELECT"))
            self.assertFalse(any(word in sql for word in ("INSERT ", "UPDATE ", "DELETE ", "DROP ")))


class AdminUiTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.role = "admin"
        self.stack.enter_context(patch("ui_client.current_user", side_effect=lambda *a: {"email": "a@example.com", "role": self.role}))
        self.stack.enter_context(patch("ui_client.list_chats", return_value={"items": [], "next_offset": None}))
        self.report = self.stack.enter_context(patch("ui_client.admin_report", return_value={
            **RAW, "satisfaction_rate": 75.0, "source_answer_rate": 75.0, "rating_coverage": 50.0}))

    def app(self, role, view=None):
        self.role = role
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "streamlit_app.py"))
        app.session_state.token = "test-only"
        app.session_state.user = {"email": "a@example.com", "role": role}
        app.session_state.messages = []
        app.session_state.expertise = "service_desk"
        if view:
            app.session_state.view = view
        return app

    def labels(self, app):
        return [button.label for button in app.button]

    def test_admin_entry_visible_only_to_admins_and_opens_panel(self):
        self.assertNotIn("Yönetim paneli", self.labels(self.app("user").run(timeout=20)))
        app = self.app("admin").run(timeout=20)
        next(b for b in app.button if b.label == "Yönetim paneli").click().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "Yönetim paneli")
        self.assertEqual(app.subheader[0].value, "Raporlama")
        self.assertIn("%75,0", [metric.value for metric in app.metric])
        self.report.assert_called_with(ANY, "test-only", 30)

    def test_non_admin_cannot_open_panel_even_with_view_flag(self):
        app = self.app("user", view="admin").run(timeout=20)
        self.assertFalse(app.exception)
        self.assertNotEqual(app.title[0].value, "Yönetim paneli")
        self.report.assert_not_called()

    def test_forbidden_response_returns_to_chat_next_run(self):
        self.report.side_effect = ui_client.ApiError(403, "Bu bölüm yalnızca yönetici hesapları içindir.")
        app = self.app("admin", view="admin").run(timeout=20)
        self.assertTrue(app.error)
        self.assertEqual(app.session_state.view, "chat")


@unittest.skipUnless(os.environ.get("ADMIN_REPORT_SQL_TEST"), "Explicit rollback-only SQL test not enabled")
class AdminSqlTests(unittest.TestCase):
    def test_real_sql_counts_change_by_seeded_turns_and_roll_back(self):
        connection = admin_service.database.connect()
        try:
            repository = MSSQLRepository(connection)
            before = repository.admin_report(30, 10)
            user = repository.create_user(f"admin-test-{uuid4()}@example.com", "test-only-not-a-login-hash")
            owner = str(user["id"])
            chat = str(repository.create_session(owner, "Rapor testi", "oracle_db")["id"])
            question = f"Rapor testi sorusu {uuid4()}"
            for rating, no_context in ((5, False), (2, True)):
                request = str(uuid4())
                repository.save_turn(owner, chat, request, question, {
                    "answer": "Yanıt", "used_source_ids": [], "sources": [], "elapsed_ms": 1000,
                    "insufficient_context": no_context})
                repository.save_feedback(owner, chat, request, rating)
            after = repository.admin_report(30, 50)
            self.assertEqual(after["users_total"] - before["users_total"], 1)
            self.assertEqual(after["questions"] - before["questions"], 2)
            self.assertEqual(after["answers"] - before["answers"], 2)
            self.assertEqual(after["answers_with_sources"] - before["answers_with_sources"], 1)
            self.assertEqual(after["rated_total"] - before["rated_total"], 2)
            self.assertEqual(after["rating_distribution"][5] - before["rating_distribution"][5], 1)
            row = next(item for item in after["top_questions"] if item["question"] == question.lower())
            self.assertEqual((row["asked"], row["rated"], row["avg_rating"]), (2, 2, 3.5))
        finally:
            connection.rollback()
            connection.close()


if __name__ == "__main__":
    unittest.main()
