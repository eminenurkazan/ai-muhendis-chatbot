"""Saved chat security, transactional retry and UI navigation without cloud calls."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest
import api
import chat_service as service
import ui_client
from mssql.repository import MSSQLRepository
from request_replay import ReplayConflict, ReplayStore

ROOT = Path(__file__).resolve().parents[1]
ANSWER = {"answer": "Türkçe **yanıt**", "used_ticket_ids": [], "retrieved_ticket_ids": [],
          "insufficient_context": False, "elapsed_ms": 12, "expertise_mode": "oracle_db",
          "prompt_version": "test", "used_source_ids": ["source-1"], "retrieved_source_ids": ["source-1"],
          "sources": [{"title": "Kaynak", "source_record_id": "source-1"}]}


@contextmanager
def identity(owner):
    previous = api.app.dependency_overrides.copy()
    api.app.dependency_overrides[api.require_user] = lambda: {"id": owner}
    try:
        yield
    finally:
        api.app.dependency_overrides.clear()
        api.app.dependency_overrides.update(previous)


class SavedTurnTests(unittest.TestCase):
    def setUp(self):
        self.owner, self.chat, self.request = [str(uuid4()) for _ in range(3)]
        self.state = {"session": {"expertise_mode": "oracle_db"}, "saved": [], "last_seq": 2,
                      "recent": [{"role": "user", "content": "İlk soru", "message_status": "completed"},
                                 {"role": "assistant", "content": "İlk yanıt", "message_status": "completed"}]}
        self.repo = Mock()
        self.repo.turn_state.side_effect = lambda *a, **kw: deepcopy(self.state)
        self.connection = Mock()
        self.stack = __import__('contextlib').ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(service.database, "connect", return_value=self.connection))
        self.stack.enter_context(patch.object(service, "MSSQLRepository", return_value=self.repo))
        self.stack.enter_context(patch.object(service, "_generated_turns", ReplayStore()))

    def run_turn(self, generate=None):
        return service.answer_chat(self.owner, self.chat, "Yeni soru", self.request,
                                   generate or Mock(return_value=ANSWER))

    def test_history_and_mode_come_from_database_and_cloud_runs_after_close(self):
        def generate(question, **options):
            self.connection.close.assert_called_once()
            self.assertEqual(question, "Yeni soru")
            self.assertEqual(options, {"expertise_mode": "oracle_db", "history": [
                {"role": "user", "content": "İlk soru"}, {"role": "assistant", "content": "İlk yanıt"}]})
            return ANSWER
        self.assertEqual(self.run_turn(generate), ANSWER)
        self.repo.save_turn.assert_called_once_with(self.owner, self.chat, self.request, "Yeni soru", ANSWER)
        self.connection.commit.assert_called_once()

    def test_saved_response_survives_generation_cache_reset_and_checks_question(self):
        self.state["saved"] = [{"role": "user", "content": "Yeni soru"},
                               {"role": "assistant", "content": ANSWER["answer"],
                                "response_json": __import__('json').dumps(ANSWER)}]
        generate = Mock()
        self.assertEqual(self.run_turn(generate), ANSWER)
        generate.assert_not_called()
        self.state["saved"][0]["content"] = "Different"
        with self.assertRaises(ReplayConflict):
            self.run_turn(generate)

    def test_failed_save_rolls_back_and_retry_reuses_generated_answer(self):
        generate = Mock(return_value=ANSWER)
        self.repo.save_turn.side_effect = [service.RepositoryError("private"), None]
        with self.assertRaises(service.ChatUnavailable):
            self.run_turn(generate)
        self.connection.rollback.assert_called_once()
        self.connection.commit.assert_not_called()
        self.assertEqual(self.run_turn(generate), ANSWER)
        generate.assert_called_once()

    def test_foreign_chat_and_changed_context_do_not_save(self):
        generate = Mock(return_value=ANSWER)
        self.repo.turn_state.side_effect = service.RecordNotFoundError()
        with self.assertRaises(service.ChatNotFound):
            self.run_turn(generate)
        generate.assert_not_called()
        changed = {**self.state, "last_seq": 4}
        self.repo.turn_state.side_effect = [self.state, changed]
        with self.assertRaises(ReplayConflict):
            self.run_turn(generate)
        self.repo.save_turn.assert_not_called()
        self.connection.rollback.assert_called_once()

    def test_api_rejects_client_history_and_requires_identity(self):
        client = TestClient(api.app)
        path = f"/chats/{self.chat}/ask"
        body = {"question": "Test", "request_id": self.request}
        self.assertEqual(client.post(path, json=body).status_code, 401)
        with identity(self.owner), patch.object(service, "answer_chat", return_value=ANSWER) as turn:
            self.assertEqual(client.post(path, json={**body, "history": []}).status_code, 422)
            self.assertEqual(client.post(path, json={**body, "expertise_mode": "windows_server"}).status_code, 422)
            self.assertEqual(client.post(path, json={"question": "Test"}).status_code, 422)
            self.assertEqual(client.post(path, json=body).json(), ANSWER)
            self.assertEqual(turn.call_args.args[:4], (self.owner, self.chat, "Test", self.request))


class SavedChatUiTests(unittest.TestCase):
    def test_relogin_loads_saved_chat_with_sources_and_continues_same_chat(self):
        chat = {"id": str(uuid4()), "title": "Oracle sorusu", "expertise_mode": "oracle_db"}
        rows = [{"role": "user", "content": "İlk soru", "message_status": "completed", "sources": []},
                {"role": "assistant", "content": "İlk yanıt", "message_status": "completed", "sources": ANSWER["sources"]}]
        app = AppTest.from_file(str(ROOT / "streamlit_app.py"))
        app.session_state.token = "test-only"
        app.session_state.user = {"email": "test@example.com"}
        app.session_state.messages = []
        app.session_state.expertise = "service_desk"
        with patch("ui_client.current_user", return_value={"email": "test@example.com"}), \
             patch("ui_client.list_chats", return_value={"items": [chat], "next_offset": None}), \
             patch("ui_client.load_messages", return_value=rows), \
             patch("ui_client.create_chat") as create, patch("ui_client.ask_saved", return_value=ANSWER) as ask:
            app.run(timeout=20)
            next(b for b in app.sidebar.button if b.label.startswith("Oracle sorusu")).click().run(timeout=20)
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state.expertise, "oracle_db")
            self.assertEqual(app.session_state.messages[1]["sources"], ANSWER["sources"])
            app.chat_input[0].set_value("Takip sorusu").run(timeout=20)
            self.assertEqual(ask.call_args.args[2:4], (chat["id"], "Takip sorusu"))
            create.assert_not_called()
            next(b for b in app.sidebar.button if b.label == "Yeni sohbet").click().run(timeout=20)
            self.assertNotIn("oracle_db", app.session_state.mode_chat_ids)
            self.assertFalse(app.session_state.messages)

    def test_client_pages_all_messages_and_keeps_authentication(self):
        chat_id = str(uuid4())
        with patch("ui_client.request_json", side_effect=[
            {"items": [{"content": "first"}], "next_after_seq": 100},
            {"items": [{"content": "last"}], "next_after_seq": None}]) as request:
            self.assertEqual(len(ui_client.load_messages("http://localhost:8000", "token", chat_id)), 2)
            self.assertIn("after_seq=100", request.call_args.args[1])
            self.assertEqual(request.call_args.kwargs["token"], "token")


@unittest.skipUnless(os.environ.get("CHAT_HISTORY_SQL_TEST"), "Explicit rollback-only SQL test not enabled")
class SavedChatSqlTests(unittest.TestCase):
    def test_complete_turn_retry_sources_owner_and_followup_with_real_sql(self):
        connection = service.database.connect()
        class View:
            autocommit = False
            def cursor(self): return connection.cursor()
            def commit(self): pass
            def rollback(self): connection.rollback()
            def close(self): pass
        try:
            repository = MSSQLRepository(connection)
            owner = str(repository.create_user(f"persist-{uuid4()}@example.com", "test-only")["id"])
            stranger = str(repository.create_user(f"persist-{uuid4()}@example.com", "test-only")["id"])
            chat_id = str(repository.create_session(owner, "Türkçe sohbet", "oracle_db")["id"])
            generate = Mock(return_value=ANSWER)
            request_id = str(uuid4())
            with patch.object(service.database, "connect", return_value=View()), patch.object(service, "_generated_turns", ReplayStore()):
                first = service.answer_chat(owner, chat_id, "İlk soru", request_id, generate)
                # Reset process cache: SQL alone must return the committed-shaped payload.
                with patch.object(service, "_generated_turns", ReplayStore()):
                    self.assertEqual(service.answer_chat(owner, chat_id, "İlk soru", request_id, generate), first)
                generate.assert_called_once()
                messages = service.list_messages(owner, chat_id)["items"]
                self.assertEqual(len(messages), 2)
                self.assertEqual(messages[1]["sources"], ANSWER["sources"])
                self.assertEqual(messages[1]["citations"], ["source-1"])
                with self.assertRaises(service.ChatNotFound):
                    service.answer_chat(stranger, chat_id, "İlk soru", request_id, generate)
                service.answer_chat(owner, chat_id, "Devam", str(uuid4()), generate)
                self.assertEqual(generate.call_args.kwargs["history"][0]["content"], "İlk soru")
                self.assertEqual(len(service.list_messages(owner, chat_id)["items"]), 4)
        finally:
            connection.rollback()
            connection.close()
