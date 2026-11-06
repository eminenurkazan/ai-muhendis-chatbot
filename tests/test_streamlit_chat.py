"""Session conversation behavior through Streamlit; all API calls are mocked."""
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import ui_client


class StreamlitChatTests(unittest.TestCase):
    def test_followup_mode_isolation_failed_requests_and_cleanup(self):
        answer = {"answer": "Gizli modda açılıyor mu?", "sources": [], "insufficient_context": True, "elapsed_ms": 10}
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "streamlit_app.py"))
        app.session_state.token = "test-only"
        app.session_state.user = {"email": "test@example.com"}
        app.session_state.messages = []
        app.session_state.expertise = "service_desk"
        with patch("ui_client.current_user", return_value={"email": "test@example.com"}), patch("ui_client.ask", return_value=answer) as ask:
            app.run(timeout=20)
            app.chat_input[0].set_value("Chrome siteleri açmıyor").run(timeout=20)
            self.assertFalse(app.exception)
            self.assertEqual(ask.call_args.kwargs["history"], [])
            app.chat_input[0].set_value("Evet, açılıyor").run(timeout=20)
            self.assertEqual(ask.call_args.kwargs["history"], [
                {"role": "user", "content": "Chrome siteleri açmıyor"},
                {"role": "assistant", "content": answer["answer"]},
            ])
            ask.side_effect = ui_client.ApiError(503, "Test hizmet hatası")
            app.chat_input[0].set_value("Başarısız soru").run(timeout=20)
            self.assertEqual(app.session_state.messages[-1]["status"], "failed")
            self.assertEqual(app.session_state.token, "test-only")
            ask.side_effect = None
            app.chat_input[0].set_value("Devam sorusu").run(timeout=20)
            sent = ask.call_args.kwargs["history"]
            self.assertEqual(len(sent), 4)
            self.assertNotIn("Başarısız soru", str(sent))
            self.assertNotIn("Devam sorusu", str(sent))
            app.sidebar.selectbox[0].select("Windows Server").run(timeout=20)
            self.assertEqual(app.session_state.messages, [])
            app.sidebar.selectbox[0].select("Servis Masası").run(timeout=20)
            self.assertEqual(len(app.session_state.messages), 7)
            next(b for b in app.sidebar.button if b.label == "Yeni sohbet").click().run(timeout=20)
            self.assertEqual(app.session_state.messages, [])
            self.assertEqual(app.session_state.token, "test-only")
            next(b for b in app.sidebar.button if b.label == "Çıkış yap").click().run(timeout=20)
            self.assertNotIn("token", app.session_state)
            self.assertNotIn("mode_messages", app.session_state)
            self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
