import os
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import patch, Mock
from uuid import uuid4
import unittest

from fastapi.testclient import TestClient
import api
import chat_service
from mssql.repository import MSSQLRepository


@contextmanager
def identity(user_id):
    old = api.app.dependency_overrides.copy()
    api.app.dependency_overrides[api.require_user] = lambda: {"id": user_id}
    try:
        yield
    finally:
        api.app.dependency_overrides.clear()
        api.app.dependency_overrides.update(old)


class ChatApiTests(unittest.TestCase):
    def test_authentication_required_for_all_routes(self):
        client = TestClient(api.app)
        chat_id = uuid4()
        for method, path in (("POST", "/chats"), ("GET", "/chats"), ("GET", f"/chats/{chat_id}"), ("GET", f"/chats/{chat_id}/messages")):
            with self.subTest(path=path):
                self.assertEqual(client.request(method, path, json={} if method == "POST" else None).status_code, 401)

    def test_owner_comes_from_auth_and_payload_is_validated(self):
        owner = str(uuid4())
        row = {"id": uuid4(), "title": "Test", "expertise_mode": "windows_server", "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc), "password_hash": "must-not-leak"}
        with identity(owner), patch("chat_service.create_chat", return_value=row) as create:
            client = TestClient(api.app)
            response = client.post("/chats", json={"title": " Test ", "expertise_mode": "windows_server"})
            self.assertEqual(response.status_code, 201)
            self.assertNotIn("password_hash", response.json())
            create.assert_called_once_with(owner, "Test", "windows_server")
            for body in ({"user_id": str(uuid4())}, {"title": " "}, {"expertise_mode": "invalid"}, {"title": "x" * 201}):
                self.assertEqual(client.post("/chats", json=body).status_code, 422)
            for path in ("/chats?offset=-1", "/chats?limit=101", "/chats/not-a-uuid", f"/chats/{uuid4()}/messages?after_seq=-1"):
                self.assertEqual(client.get(path).status_code, 422)
            create.assert_called_once()

    def test_not_found_and_database_errors_are_safe(self):
        with identity(str(uuid4())), patch("chat_service.get_chat", side_effect=chat_service.ChatNotFound("Sohbet bulunamadı.")):
            response = TestClient(api.app).get(f"/chats/{uuid4()}")
            self.assertEqual(response.status_code, 404)
        with patch.object(chat_service.database, "connect", side_effect=chat_service.database.MSSQLConnectionError("secret-connection")):
            with self.assertRaises(chat_service.ChatUnavailable) as caught:
                chat_service.list_chats(str(uuid4()))
            self.assertNotIn("secret-connection", str(caught.exception))

    def test_write_failure_rolls_back_and_closes(self):
        connection = Mock()
        with patch.object(chat_service.database, "connect", return_value=connection), patch.object(chat_service, "MSSQLRepository", side_effect=RuntimeError("test")):
            with self.assertRaises(RuntimeError):
                chat_service.create_chat(str(uuid4()), "Test", "service_desk")
        connection.rollback.assert_called_once()
        connection.close.assert_called_once()
        connection.commit.assert_not_called()


class RepositoryPagingTests(unittest.TestCase):
    def test_chat_list_binds_user_offset_and_limit(self):
        repository = object.__new__(MSSQLRepository)
        repository._query = Mock(return_value=[])
        owner = str(uuid4())
        repository.list_sessions(owner, offset=10, limit=51)
        args = repository._query.call_args.args
        self.assertIn("s.user_id = ?", args[0])
        self.assertIn("OFFSET ? ROWS FETCH NEXT ? ROWS ONLY", args[0])
        self.assertEqual(args[1:], (owner, 10, 51))

    def test_message_list_checks_ownership_and_binds_limit(self):
        repository = object.__new__(MSSQLRepository)
        repository._query = Mock(return_value=[])
        repository._owned_session = Mock()
        owner, chat_id = str(uuid4()), str(uuid4())
        repository.list_messages(owner, chat_id, after_seq=3, limit=51)
        repository._owned_session.assert_called_once_with(owner, chat_id)
        args = repository._query.call_args.args
        self.assertIn("s.user_id = ?", args[0])
        self.assertIn("SELECT TOP (?)", args[0])
        self.assertEqual(args[1:], (51, chat_id, 3, owner))

@unittest.skipUnless(os.environ.get("CHAT_HISTORY_SQL_TEST"), "Explicit rollback-only SQL test not enabled")
class ChatSqlTests(unittest.TestCase):
    def test_real_sql_ownership_pagination_and_sources_with_rollback(self):
        connection = chat_service.database.connect()
        class TransactionView:
            autocommit = False
            def cursor(self): return connection.cursor()
            def commit(self): pass  # All fixture writes stay in this test transaction.
            def rollback(self): connection.rollback()
            def close(self): pass
        try:
            repository = MSSQLRepository(connection)
            first = repository.create_user(f"chat-test-{uuid4()}@example.com", "test-only-not-a-login-hash")
            second = repository.create_user(f"chat-test-{uuid4()}@example.com", "test-only-not-a-login-hash")
            owner, stranger = str(first["id"]), str(second["id"])
            with patch.object(chat_service.database, "connect", return_value=TransactionView()), identity(owner):
                client = TestClient(api.app)
                response = client.post("/chats", json={"title": "Test history", "expertise_mode": "windows_server"})
                self.assertEqual(response.status_code, 201, response.text)
                chat_id = response.json()["id"]
                repository.create_session(owner, "Other", "service_desk")
                repository.add_message(owner, chat_id, "user", "Question")
                repository.add_message(owner, chat_id, "assistant", "Answer", citations=["source-1"], source_snapshot=[{"title": "Source"}])
                page = client.get("/chats?limit=1").json()
                self.assertEqual(len(page["items"]), 1)
                self.assertEqual(page["next_offset"], 1)
                self.assertEqual(len(client.get("/chats?limit=1&offset=1").json()["items"]), 1)
                first_page = client.get(f"/chats/{chat_id}/messages?limit=1").json()
                self.assertEqual(first_page["items"][0]["content"], "Question")
                next_seq = first_page["next_after_seq"]
                last = client.get(f"/chats/{chat_id}/messages?limit=1&after_seq={next_seq}").json()
                self.assertEqual(last["items"][0]["citations"], ["source-1"])
                self.assertEqual(last["items"][0]["sources"], [{"title": "Source"}])
                self.assertIsNone(last["next_after_seq"])
                self.assertTrue(last["items"][0]["created_at"].endswith("Z"))
                with identity(stranger):
                    self.assertEqual(client.get("/chats").json()["items"], [])
                    for suffix in ("", "/messages"):
                        forbidden = client.get(f"/chats/{chat_id}{suffix}")
                        missing = client.get(f"/chats/{uuid4()}{suffix}")
                        self.assertEqual(forbidden.status_code, 404)
                        self.assertEqual(forbidden.json(), missing.json())
        finally:
            connection.rollback()
            connection.close()
