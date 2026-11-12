"""Retry behavior with fake API responses and synchronized fake work only."""
from pathlib import Path
from threading import Event, Thread
from unittest.mock import Mock, patch
from uuid import uuid4
import unittest

from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

import api
import ui_client
from request_replay import ReplayStore, ReplayConflict, ReplayBusy


ANSWER = {"answer": "Gizli modda açılıyor mu?", "sources": [], "insufficient_context": True, "elapsed_ms": 10}


def app_for_test():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "streamlit_app.py"))
    app.session_state.token = "test-token"
    app.session_state.user = {"email": "test@example.com"}
    app.session_state.messages = []
    app.session_state.expertise = "service_desk"
    return app


def retry_button(app):
    return next(b for b in app.button if b.label == "Tekrar dene")


class RetryUiTests(unittest.TestCase):

    def setUp(self):
        from uuid import uuid4
        for name, value in (("list_chats", {"items": [], "next_offset": None}),
                            ("create_chat", {"id": str(uuid4())})):
            active = patch("ui_client." + name, return_value=value)
            active.start()
            self.addCleanup(active.stop)

    def test_transient_failures_retry_same_request_and_history_without_duplicate_messages(self):
        for status in (None, 502, 503):
            with self.subTest(status=status):
                app = app_for_test()
                with patch("ui_client.current_user", return_value={"email": "test@example.com"}), patch(
                    "ui_client.ask_saved", side_effect=[ANSWER, ui_client.ApiError(status, "Test hatası"), ANSWER]
                ) as ask:
                    app.run(timeout=20)
                    app.chat_input[0].set_value("Chrome açmıyor").run(timeout=20)
                    app.chat_input[0].set_value("Evet açılıyor").run(timeout=20)
                    self.assertFalse(app.exception)
                    self.assertEqual(len(app.session_state.messages), 3)
                    self.assertEqual(app.session_state.token, "test-token")
                    failed_call = ask.call_args
                    app.run(timeout=20)
                    self.assertEqual(ask.call_count, 2, "A rerun must not automatically retry")
                    self.assertTrue(retry_button(app))
                    retry_button(app).click().run(timeout=20)
                    self.assertEqual(ask.call_args, failed_call)
                    self.assertEqual(ask.call_count, 3)
                    self.assertEqual(len(app.session_state.messages), 4)
                    self.assertEqual([m["content"] for m in app.session_state.messages].count("Evet açılıyor"), 1)
                    self.assertFalse(app.session_state.pending_requests)
                    self.assertFalse(app.exception)

    def test_pending_request_is_isolated_and_new_conversation_discards_it(self):
        app = app_for_test()
        with patch("ui_client.current_user", return_value={"email": "test@example.com"}), patch("ui_client.ask_saved", side_effect=ui_client.ApiError(503, "Test")) as ask:
            app.run(timeout=20)
            app.chat_input[0].set_value("Test sorusu").run(timeout=20)
            pending = app.session_state.pending_requests["service_desk"]
            pending["running"] = True
            app.run(timeout=20)
            self.assertTrue(retry_button(app).disabled)
            self.assertTrue(app.chat_input[0].disabled)
            self.assertEqual(ask.call_count, 1)
            pending["running"] = False
            app.sidebar.selectbox[0].select("Windows Server").run(timeout=20)
            self.assertFalse(any(b.label == "Tekrar dene" for b in app.button))
            self.assertFalse(app.session_state.messages)
            app.sidebar.selectbox[0].select("Servis Masası").run(timeout=20)
            self.assertTrue(retry_button(app))
            next(b for b in app.sidebar.button if b.label == "Yeni sohbet").click().run(timeout=20)
            self.assertFalse(app.session_state.pending_requests)
            self.assertFalse(app.session_state.messages)
            self.assertEqual(ask.call_count, 1)

    def test_auth_failure_clears_user_state_and_validation_failure_has_no_retry(self):
        for status in (401, 422):
            app = app_for_test()
            with patch("ui_client.current_user", return_value={"email": "test@example.com"}), patch("ui_client.ask_saved", side_effect=ui_client.ApiError(status, "Test")):
                app.run(timeout=20)
                app.chat_input[0].set_value("Test sorusu").run(timeout=20)
                self.assertFalse(app.exception)
                self.assertFalse(any(b.label == "Tekrar dene" for b in app.button))
                if status == 401:
                    self.assertNotIn("token", app.session_state)
                    self.assertNotIn("pending_requests", app.session_state)
                else:
                    self.assertEqual(app.session_state.token, "test-token")

    def test_api_offline_keeps_cached_session_and_retry_controls(self):
        app = app_for_test()
        with patch("ui_client.current_user", side_effect=ui_client.ApiError(None, "Offline")), patch("ui_client.ask_saved", side_effect=ui_client.ApiError(None, "Offline")) as ask:
            app.run(timeout=20)
            app.chat_input[0].set_value("Test sorusu").run(timeout=20)
            self.assertTrue(retry_button(app))
            self.assertEqual(app.session_state.token, "test-token")
            self.assertEqual(ask.call_count, 1)
            self.assertFalse(app.exception)


class ReplayTests(unittest.TestCase):
    def test_completed_result_is_reused_only_for_same_owner_and_payload(self):
        store = ReplayStore()
        work = Mock(return_value={"answer": "OK"})
        self.assertEqual(store.run("user-1", "id", {"question": "Q"}, work), {"answer": "OK"})
        result = store.run("user-1", "id", {"question": "Q"}, work)
        result["answer"] = "mutated"
        self.assertEqual(store.run("user-1", "id", {"question": "Q"}, work)["answer"], "OK")
        work.assert_called_once()
        with self.assertRaises(ReplayConflict):
            store.run("user-1", "id", {"question": "different"}, work)
        store.run("user-2", "id", {"question": "Q"}, work)
        self.assertEqual(work.call_count, 2)

    def test_inflight_duplicate_cannot_start_work_again(self):
        store = ReplayStore()
        entered, release = Event(), Event()
        def work():
            entered.set()
            if not release.wait(5):
                raise RuntimeError("Test synchronization failed")
            return "OK"
        operation = Mock(side_effect=work)
        thread = Thread(target=lambda: store.run("user", "id", {}, operation))
        thread.start()
        try:
            self.assertTrue(entered.wait(5))
            with self.assertRaises(ReplayConflict):
                store.run("user", "id", {}, operation)
        finally:
            release.set()
            thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(store.run("user", "id", {}, operation), "OK")
        operation.assert_called_once()

    def test_failures_allow_explicit_retry_and_cache_capacity_is_bounded(self):
        store = ReplayStore(capacity=1, ttl=10)
        work = Mock(side_effect=[RuntimeError("Test"), "OK"])
        with self.assertRaises(RuntimeError):
            store.run("user", "id", {}, work)
        self.assertEqual(store.run("user", "id", {}, work), "OK")
        with self.assertRaises(ReplayBusy):
            store.run("user", "other", {}, work)
        self.assertEqual(len(store.entries), 1)
        with patch("request_replay.time.monotonic", return_value=store.entries[("user", "id")]["finished"] + 11):
            self.assertEqual(store.run("user", "other", {}, lambda: "NEXT"), "NEXT")

    def test_authenticated_api_replays_response_without_repeating_rag(self):
        response = {**ANSWER, "used_ticket_ids": [], "retrieved_ticket_ids": [], "expertise_mode": "service_desk",
                    "prompt_version": "test", "used_source_ids": [], "retrieved_source_ids": []}
        body = {"question": "Test", "request_id": str(uuid4())}
        old = api.app.dependency_overrides.copy()
        api.app.dependency_overrides[api.require_user] = lambda: {"id": "user-1"}
        try:
            with patch.object(api, "replays", ReplayStore()), patch("rag_service.ask_question", return_value=response) as rag:
                client = TestClient(api.app)
                first = client.post("/ask", json=body)
                second = client.post("/ask", json=body)
                self.assertEqual(first.status_code, 200)
                self.assertEqual(first.json(), second.json())
                rag.assert_called_once()
                self.assertEqual(client.post("/ask", json={**body, "question": "Changed"}).status_code, 409)
                api.app.dependency_overrides.clear()
                self.assertEqual(client.post("/ask", json=body).status_code, 401)
                rag.assert_called_once()
        finally:
            api.app.dependency_overrides.clear()
            api.app.dependency_overrides.update(old)


if __name__ == "__main__":
    unittest.main()
