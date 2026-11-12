"""Feedback ownership, idempotent updates and dialog interactions; no cloud calls."""
from contextlib import ExitStack
import os
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest
import api
import chat_service
import ui_client
from mssql.repository import MSSQLRepository, RecordNotFoundError, RepositoryError


class FeedbackApiTests(unittest.TestCase):
    def setUp(self):
        self.owner, self.chat, self.request = [str(uuid4()) for _ in range(3)]
        self.url = f"/chats/{self.chat}/requests/{self.request}/feedback"
        self.previous = api.app.dependency_overrides.copy()
        self.addCleanup(self.restore_identity)
        self.client = TestClient(api.app)

    def restore_identity(self):
        api.app.dependency_overrides.clear()
        api.app.dependency_overrides.update(self.previous)

    def test_requires_auth_and_uses_only_jwt_owner(self):
        self.assertEqual(self.client.put(self.url, json={"rating": 5}).status_code, 401)
        api.app.dependency_overrides[api.require_user] = lambda: {"id": self.owner}
        with patch("chat_service.save_feedback", return_value={"rating": 5, "comment": "Yararlı"}) as save:
            result = self.client.put(self.url, json={"rating": 5, "comment": "Yararlı"})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json(), {"rating": 5, "comment": "Yararlı"})
            save.assert_called_once_with(self.owner, self.chat, self.request, 5, "Yararlı")

    def test_rejects_invalid_rating_comment_and_owner_fields(self):
        api.app.dependency_overrides[api.require_user] = lambda: {"id": self.owner}
        with patch("chat_service.save_feedback") as save:
            for body in ({"rating": 0}, {"rating": 6}, {"rating": True}, {"rating": "5"},
                         {"rating": 4.5}, {"rating": 5, "comment": "x" * 2001},
                         {"rating": 5, "user_id": self.owner}):
                with self.subTest(body=str(body)[:50]):
                    self.assertEqual(self.client.put(self.url, json=body).status_code, 422)
            save.assert_not_called()

    def test_not_found_and_connection_failures_are_safe(self):
        api.app.dependency_overrides[api.require_user] = lambda: {"id": self.owner}
        for error, status in ((chat_service.ChatNotFound("Sohbet bulunamadı."), 404),
                              (chat_service.ChatUnavailable("Şu anda ulaşılamıyor."), 503)):
            with patch("chat_service.save_feedback", side_effect=error):
                self.assertEqual(self.client.put(self.url, json={"rating": 4}).status_code, status)


class FeedbackRepositoryTests(unittest.TestCase):
    def test_update_is_parameterized_and_only_completed_assistant_is_selected(self):
        repository = object.__new__(MSSQLRepository)
        repository._owned_session = Mock()
        message_id = str(uuid4())
        repository._query = Mock(side_effect=[[{"id": message_id}], [{"id": uuid4()}], []])
        owner, chat, request = [str(uuid4()) for _ in range(3)]
        comment = "'; DROP TABLE users; -- Türkçe"
        self.assertEqual(repository.save_feedback(owner, chat, request, 4, comment),
                         {"rating": 4, "comment": comment})
        repository._owned_session.assert_called_once_with(owner, chat, lock=True)
        sql = repository._query.call_args_list[0].args[0]
        self.assertIn("role=N'assistant'", sql)
        self.assertIn("message_status=N'completed'", sql)
        update = repository._query.call_args.args
        self.assertNotIn(comment, update[0])
        self.assertEqual(update[1:], (4, comment, message_id))

    def test_missing_or_non_assistant_answer_is_not_rateable(self):
        repository = object.__new__(MSSQLRepository)
        repository._owned_session = Mock()
        repository._query = Mock(return_value=[])
        with self.assertRaises(RecordNotFoundError):
            repository.save_feedback(*[str(uuid4()) for _ in range(3)], 5)
        self.assertEqual(repository._query.call_count, 1)

    def test_write_failure_rolls_back_and_closes(self):
        connection, repository = Mock(), Mock()
        repository.save_feedback.side_effect = RepositoryError("private SQL details")
        with patch.object(chat_service.database, "connect", return_value=connection), \
             patch.object(chat_service, "MSSQLRepository", return_value=repository):
            with self.assertRaises(chat_service.ChatUnavailable) as error:
                chat_service.save_feedback(*[str(uuid4()) for _ in range(3)], 5)
        self.assertNotIn("private", str(error.exception))
        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()
        connection.close.assert_called_once()


class FeedbackUiTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch("ui_client.current_user", return_value={"email": "test@example.com"}))
        self.stack.enter_context(patch("ui_client.list_chats", return_value={"items": [], "next_offset": None}))
        self.save = self.stack.enter_context(patch("ui_client.save_feedback", return_value={"rating": 4, "comment": "Yararlı"}))
        self.app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "streamlit_app.py"))
        self.chat, self.request = str(uuid4()), str(uuid4())
        self.app.session_state.token = "test-only"
        self.app.session_state.user = {"email": "test@example.com"}
        self.app.session_state.expertise = "service_desk"
        self.app.session_state.messages = [
            {"role": "user", "content": "Soru", "status": "complete"},
            {"role": "assistant", "content": "Yanıt", "status": "complete",
             "chat_id": self.chat, "request_id": self.request}]

    def button(self, label):
        return next(button for button in self.app.button if button.label == label)

    def submit_form(self):
        # AppTest runs the whole script, whereas a browser dialog reruns its fragment.
        # Keep the invitation active for that simulated full-script form submission.
        self.button("Değerlendir").set_value(True)
        self.button("Değerlendirmeyi kaydet").click().run(timeout=20)

    def test_invitation_dismissal_never_becomes_conversation_content(self):
        self.app.run(timeout=20)
        self.assertTrue(self.button("Değerlendir"))
        self.button("Şimdi değil").click().run(timeout=20)
        self.assertFalse(self.app.exception)
        self.assertEqual(len(self.app.session_state.messages), 2)
        self.assertFalse(any(button.label == "Değerlendir" for button in self.app.button))
        self.save.assert_not_called()

    def test_popup_requires_rating_then_saves_and_can_be_edited(self):
        self.app.run(timeout=20)
        self.button("Değerlendir").click().run(timeout=20)
        self.assertFalse(self.app.exception)
        self.submit_form()
        self.save.assert_not_called()
        self.assertTrue(self.app.warning)
        self.app.radio[0].set_value(4)
        self.app.text_area[0].set_value("Yararlı")
        self.submit_form()
        self.assertFalse(self.app.exception)
        self.save.assert_called_once_with(unittest.mock.ANY, "test-only", self.chat, self.request, 4, "Yararlı")
        self.assertEqual(self.app.session_state.messages[1]["feedback_rating"], 4)
        self.assertTrue(self.button("Değerlendirmeyi düzenle"))
        self.assertEqual(len(self.app.session_state.messages), 2)

    def test_failed_save_keeps_form_and_allows_explicit_retry(self):
        self.save.side_effect = ui_client.ApiError(503, "Unavailable")
        self.app.run(timeout=20)
        self.button("Değerlendir").click().run(timeout=20)
        self.app.radio[0].set_value(4)
        self.app.text_area[0].set_value("Yararlı")
        self.submit_form()
        self.assertTrue(self.app.error)
        self.assertNotIn("feedback_rating", self.app.session_state.messages[1])
        self.assertEqual(self.app.text_area[0].value, "Yararlı")
        self.save.side_effect = None
        self.submit_form()
        self.assertEqual(self.app.session_state.messages[1]["feedback_rating"], 4)


@unittest.skipUnless(os.environ.get("CHAT_HISTORY_SQL_TEST"), "Explicit SQL test not enabled")
class FeedbackSqlTests(unittest.TestCase):
    def test_real_sql_ownership_update_and_history_readback_with_rollback(self):
        connection = chat_service.database.connect()
        class View:
            autocommit = False
            def cursor(self): return connection.cursor()
            def commit(self): pass
            def rollback(self): connection.rollback()
            def close(self): pass
        try:
            repository = MSSQLRepository(connection)
            owner = str(repository.create_user(f"feedback-{uuid4()}@example.com", "test-only")["id"])
            stranger = str(repository.create_user(f"feedback-{uuid4()}@example.com", "test-only")["id"])
            chat = str(repository.create_session(owner, "Feedback", "service_desk")["id"])
            request = str(uuid4())
            # A user message alone cannot be rated.
            repository.add_message(owner, chat, "user", "Soru", request_id=request)
            with self.assertRaises(RecordNotFoundError):
                repository.save_feedback(owner, chat, request, 5)
            repository.add_message(owner, chat, "assistant", "Yanıt", request_id=request)
            with self.assertRaises(RecordNotFoundError):
                repository.save_feedback(stranger, chat, request, 5)
            with patch.object(chat_service.database, "connect", return_value=View()):
                chat_service.save_feedback(owner, chat, request, 3, "İlk puan")
                chat_service.save_feedback(owner, chat, request, 5, "Türkçe yorum")
                rows = chat_service.list_messages(owner, chat)["items"]
                self.assertIsNone(rows[0]["feedback_rating"])
                self.assertEqual(rows[1]["feedback_rating"], 5)
                self.assertEqual(rows[1]["feedback_comment"], "Türkçe yorum")
                count = connection.cursor().execute(
                    "SELECT COUNT(*) FROM dbo.feedback WHERE message_id=?", str(rows[1]["id"])
                ).fetchone()[0]
                self.assertEqual(count, 1)
        finally:
            connection.rollback()
            connection.close()
